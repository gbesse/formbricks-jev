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

`yes`, `no`, `review`, `failure`; threshold default `0.8`. `review` is a real undecided state. Empty or oversized input becomes `review`; transport or invalid-response errors become `failure`. The shared client caps input at 32 KiB, response at 100 KiB, timeout at 10 s and calls at 10,000 per process; YAML templates enforce their own input and response bounds. No raw input is logged by this project. User data goes to the TypeSafe Jev API.

FR : `review` exige une revue humaine ; `failure` signale une erreur. Le contenu est envoyé à l’API TypeSafe Jev.

ES: `review` requiere revisión humana; `failure` indica un error. El contenido se envía a la API TypeSafe Jev.

## TLS / TLS / TLS

FR : si votre installation Python ne trouve pas les certificats racines, définissez `SSL_CERT_FILE` vers un bundle CA valide (par exemple `certifi.where()`). Ne désactivez pas la vérification TLS.

EN: if Python cannot find root certificates, set `SSL_CERT_FILE` to a valid CA bundle (for example `certifi.where()`). Keep TLS verification enabled.

ES: si Python no encuentra los certificados raíz, defina `SSL_CERT_FILE` con un paquete CA válido (por ejemplo `certifi.where()`). Mantenga activa la verificación TLS.

## Development / Développement / Desarrollo

`python -m unittest discover -p "test_*.py" -v`

Platform / Plateforme / Plataforma: [Formbricks Hub documentation](https://hub.formbricks.com/core-concepts/webhooks).

MIT license. Community project; not an official Formbricks Hub integration.
