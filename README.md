# formbricks-jev

## Français

Récepteur de webhooks signés avec décisions idempotentes dans SQLite.

Installez les dépendances, définissez les trois variables, démarrez le serveur et enregistrez `/webhook` dans Hub. Les décisions sont conservées dans SQLite.

## English

Signed webhook receiver with idempotent decisions in SQLite.

Install `requirements.txt`; set `FORMBRICKS_WEBHOOK_SECRET`, `JEV_QUESTION`, `JEV_API_KEY`; run `python formbricks_jev.py` and register `https://your-host/webhook` for `feedback_record.created` and `.updated` in Hub. Decisions are stored in `decisions.sqlite3` keyed by `webhook-id`. Terminate TLS at a reverse proxy. A failed Jev call returns 503 so Hub can retry.

## Español

Receptor de webhooks firmados con decisiones idempotentes en SQLite.

Instale las dependencias, defina las tres variables, inicie el servidor y registre `/webhook` en Hub. Las decisiones se guardan en SQLite.

## Contract / Contrat / Contrato

FR : le seuil par défaut est `0.8`. Les routes sont `yes`, `no`, `review` et `failure`. Une entrée vide ou supérieure à 32 Kio donne `review` ; une erreur de transport ou de réponse donne `failure`. Le client limite les appels à 10 000 par processus, à 10 s par appel et à 100 Kio par réponse. Un cache LRU conserve au plus 1 024 verdicts valides par empreinte SHA-256 ; il ne conserve pas le texte brut. Les données sont envoyées à TypeSafe Jev.

EN: the default threshold is `0.8`. Routes are `yes`, `no`, `review`, and `failure`. Empty input or input over 32 KiB becomes `review`; transport or response errors become `failure`. The client caps calls at 10,000 per process, 10 seconds per call, and 100 KiB per response. An LRU cache keeps at most 1,024 valid verdicts by SHA-256 digest; it does not store raw text. Data is sent to TypeSafe Jev.

ES: el umbral predeterminado es `0.8`. Las rutas son `yes`, `no`, `review` y `failure`. Una entrada vacía o superior a 32 KiB produce `review`; los errores de transporte o respuesta producen `failure`. El cliente limita las llamadas a 10 000 por proceso, a 10 s por llamada y a 100 KiB por respuesta. Una caché LRU conserva como máximo 1 024 decisiones válidas por huella SHA-256; no almacena el texto original. Los datos se envían a TypeSafe Jev.

## Decisions API / API des décisions / API de decisiones

FR : les signatures Standard Webhooks sont vérifiées sur les octets reçus. Une livraison concurrente du même événement reçoit `503` et sera réessayée par Hub ; une décision déjà enregistrée est renvoyée sans nouvel appel Jev. Définissez `FORMBRICKS_JEV_ADMIN_TOKEN` pour lire un verdict par `GET /decisions?event_id=...`. `GET /healthz` sert aux sondes. La base SQLite existante est conservée.

EN: Standard Webhooks signatures are verified on raw bytes. A concurrent delivery of the same event receives `503` for Hub to retry; a stored decision is returned without another Jev call. Set `FORMBRICKS_JEV_ADMIN_TOKEN` to read a verdict with `GET /decisions?event_id=...`. Use `GET /healthz` for probes. Existing SQLite data is preserved.

ES: las firmas Standard Webhooks se verifican sobre los bytes originales. Una entrega concurrente del mismo evento recibe `503` para que Hub la reintente; una decisión guardada se devuelve sin otra llamada a Jev. Defina `FORMBRICKS_JEV_ADMIN_TOKEN` para leer un resultado con `GET /decisions?event_id=...`. Use `GET /healthz` para las sondas. Se conservan los datos SQLite existentes.

```sh
curl -H "Authorization: Bearer $FORMBRICKS_JEV_ADMIN_TOKEN" \
  'http://127.0.0.1:8080/decisions?event_id=evt_123'
```

FR : une image Docker exécutable sans privilèges est fournie. Montez un volume persistant sur `/data` et transmettez les secrets comme variables d’environnement, jamais dans l’image.

EN: a non-root Docker image is provided. Mount persistent storage at `/data` and pass secrets as environment variables, never into the image.

ES: se incluye una imagen Docker sin privilegios. Monte almacenamiento persistente en `/data` y pase los secretos como variables de entorno, nunca dentro de la imagen.

```sh
docker build -t formbricks-jev .
docker run --rm -p 8080:8080 -v formbricks-jev-data:/data \
  -e FORMBRICKS_WEBHOOK_SECRET -e JEV_QUESTION -e JEV_API_KEY \
  -e FORMBRICKS_JEV_ADMIN_TOKEN formbricks-jev
```

## TLS / TLS / TLS

FR : si votre installation Python ne trouve pas les certificats racines, définissez `SSL_CERT_FILE` vers un bundle CA valide (par exemple `certifi.where()`). Ne désactivez pas la vérification TLS.

EN: if Python cannot find root certificates, set `SSL_CERT_FILE` to a valid CA bundle (for example `certifi.where()`). Keep TLS verification enabled.

ES: si Python no encuentra los certificados raíz, defina `SSL_CERT_FILE` con un paquete CA válido (por ejemplo `certifi.where()`). Mantenga activa la verificación TLS.

## Development / Développement / Desarrollo

`python -m unittest discover -p "test_*.py" -v`

Platform / Plateforme / Plataforma: [Formbricks Hub documentation](https://hub.formbricks.com/core-concepts/webhooks).

MIT license. Community project; not an official Formbricks Hub integration.
