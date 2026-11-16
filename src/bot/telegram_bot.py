"""Bot Telegram optionnel, identité liée côté API, conversations privées uniquement."""
import os
import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

API = os.getenv("API_URL", "http://127.0.0.1:8000")


async def private(update):
    if not update.effective_chat or update.effective_chat.type != "private":
        return False
    return bool(update.effective_user)


async def api(update, method, path, **kwargs):
    if not await private(update):
        raise PermissionError("Utilisez une conversation privée")
    async with httpx.AsyncClient(timeout=65) as client:
        session = await client.post(API+f"/telegram/session/{update.effective_user.id}", headers={"X-Bot-Secret":os.environ["TELEGRAM_BRIDGE_SECRET"]})
        if not session.is_success:
            raise PermissionError("Associez votre compte avec /link CODE depuis l'interface web")
        payload = session.json()
        token = payload["access_token"]
        headers = {"Authorization":"Bearer "+token}
        try:
            response = await client.request(method, API+path, headers=headers, **kwargs)
            if not response.is_success:
                raise ValueError(str(response.json().get("detail","Requête refusée")))
            return response.json(), payload["user"]
        finally:
            await client.post(API+"/auth/logout",headers=headers)


async def reply(update, text):
    if await private(update):
        await update.effective_message.reply_text(text[:3900])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update, "OrdoPlan · atelier fictif. Associez votre compte depuis le web avec /link CODE.\n/ask QUESTION · /plan · /breakdown CNC-B DEBUT_MIN DUREE_MIN · /urgent DEBUT_MIN\n/history · /orders · /draft ID · /approve ID HASH · /publish ID · /cancel ID\nEnvoyez une photo pour une lecture locale à confirmer. /unlink pour dissocier le compte.")


async def link(update, context):
    if not await private(update):
        return
    if len(context.args) != 1:
        return await reply(update, "Usage : /link CODE")
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(API+"/telegram/link",headers={"X-Bot-Secret":os.environ["TELEGRAM_BRIDGE_SECRET"]},json={"code":context.args[0],"telegram_id":str(update.effective_user.id)})
    await reply(update,"Compte associé." if r.is_success else "Association refusée : code invalide ou expiré.")


def answer_text(result):
    text = result.get("answer", "")
    for c in result.get("citations", [])[:3]:
        text += f"\nSource : {c['document_id']}, p.{c['page']}, {c['element_id']}"
    if result.get("clarification_question"):
        text += "\n"+result["clarification_question"]
    if result.get("proposed_action"):
        action = result["proposed_action"]
        text += f"\nBrouillon : {action['draft_id']}\nEmpreinte : {action['hash']}\nConsultez /draft {action['draft_id']} avant l'accord."
    return text


async def ask(update, context):
    question = " ".join(context.args)
    if not question:
        return await reply(update, "Usage : /ask QUESTION")
    _, user = await api(update, "GET", "/auth/me")
    result, _ = await api(update,"POST","/assistant",json={"workshop_id":user["workshop"],"mode":"question","question":question})
    await reply(update,answer_text(result))


async def plan(update, context):
    _, user = await api(update,"GET","/auth/me")
    body = {"workshop_id":user["workshop"],"mode":"plan","question":"Planning atelier et arbitrages vérifiés."}
    command = update.effective_message.text.split()[0].split("@")[0]
    if command in ("/breakdown","/urgent"):
        if not context.user_data.get("baseline"):
            return await reply(update,"Calculez d'abord /plan.")
        body["baseline_draft_id"] = context.user_data["baseline"]
        if command == "/breakdown":
            if len(context.args) != 3:
                return await reply(update,"Usage : /breakdown CNC-B DEBUT_MIN DUREE_MIN. Les minutes partent de 08:00 ; l'envoi confirme ces valeurs.")
            body["event"] = {"kind":"breakdown","machine_id":context.args[0],"start":int(context.args[1]),"duration":int(context.args[2])}
        else:
            if len(context.args) != 1:
                return await reply(update,"Usage : /urgent DEBUT_MIN")
            body["event"] = {"kind":"urgent","start":int(context.args[0])}
    result, _ = await api(update,"POST","/assistant",json=body)
    if result.get("proposed_action"):
        context.user_data["baseline"] = result["proposed_action"]["draft_id"]
    await reply(update,answer_text(result))


async def photo(update, context):
    if not await private(update):
        return
    await api(update,"GET","/auth/me")
    file = await update.effective_message.photo[-1].get_file()
    if file.file_size and file.file_size > 8*1024*1024:
        return await reply(update,"Photographie supérieure à 8 Mo")
    content = bytes(await file.download_as_bytearray())
    result, _ = await api(update,"POST","/analyze",files={"file":("photo.jpg",content,"image/jpeg")})
    await reply(update,str(result["observation"])+"\n"+"\n".join(result["uncertainties"])+"\nConfirmez les valeurs dans /breakdown ou dans l'interface web avant un calcul.")


async def history(update, context):
    result,_ = await api(update,"GET","/publications")
    await reply(update,str(result) if result else "Aucune publication MES.")


async def orders(update, context):
    _,user = await api(update,"GET","/auth/me")
    result,_ = await api(update,"POST","/assistant",json={"mode":"question","workshop_id":user["workshop"],"question":"Carnet ERP OF-101 quantité échéance"})
    await reply(update,answer_text(result))


async def draft(update, context):
    if len(context.args) != 1:
        return await reply(update,"Usage : /draft ID")
    result,_ = await api(update,"GET","/drafts/"+context.args[0])
    lines = [f"{p['order_id']} {p['machine']} {p['start']}→{p['end']} min après 08:00, réglage {p['setup']} min" for p in result["payload"]["schedule"]["operations"]]
    await reply(update,"\n".join(lines)+"\nEmpreinte : "+result["hash"]+f"\nSi vous approuvez ce contenu exact : /approve {result['id']} {result['hash']}")


async def approve(update, context):
    if len(context.args) != 2:
        return await reply(update,"Usage : /approve ID HASH après lecture de /draft ID")
    result,_ = await api(update,"POST",f"/drafts/{context.args[0]}/approve",json={"hash":context.args[1],"confirmed":True})
    context.user_data["approval"] = {"draft":context.args[0],"token":result["approval_token"]}
    await reply(update,"Accord enregistré pour 5 minutes. Publier : /publish "+context.args[0])


async def publish(update, context):
    approval = context.user_data.get("approval",{})
    if len(context.args) != 1 or approval.get("draft") != context.args[0]:
        return await reply(update,"Approbation de ce brouillon requise.")
    result,_ = await api(update,"POST",f"/drafts/{context.args[0]}/publish",json={"approval_token":approval["token"]})
    await reply(update,"Publication MES : "+str(result))


async def cancel(update, context):
    if len(context.args) != 1:
        return await reply(update,"Usage : /cancel ID")
    await api(update,"POST",f"/drafts/{context.args[0]}/cancel")
    context.user_data.pop("approval",None)
    await reply(update,"Brouillon annulé.")


async def unlink(update, context):
    await api(update,"DELETE","/telegram/link")
    context.user_data.clear()
    await reply(update,"Compte dissocié.")


async def error(update, context):
    if update:
        await reply(update,"Requête non exécutée : "+str(context.error)[:300])


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token or not os.environ.get("TELEGRAM_BRIDGE_SECRET"):
        raise SystemExit("Configurer TELEGRAM_BOT_TOKEN et TELEGRAM_BRIDGE_SECRET dans l'environnement avant de lancer le bot.")
    application = ApplicationBuilder().token(token).build()
    handlers = {"start":start,"link":link,"ask":ask,"plan":plan,"breakdown":plan,"urgent":plan,"analyze":start,"history":history,"orders":orders,"draft":draft,"approve":approve,"publish":publish,"cancel":cancel,"unlink":unlink}
    for name, callback in handlers.items():
        application.add_handler(CommandHandler(name,callback))
    application.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE,photo))
    application.add_error_handler(error)
    application.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
