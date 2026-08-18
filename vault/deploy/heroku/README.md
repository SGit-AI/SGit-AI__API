[🏠 Deploy Hub](../../00-START-HERE.md) › **Heroku**

# Deploy on Heroku

**Status: 🚧 planned (Phase D2)** — the repo already carries the button contract
(`app.json` + `heroku.yml`, container stack). What works today, manually:

```bash
heroku create my-sg-send --stack container
heroku container:login
docker pull diniscruz/sg-send-vault:latest
docker tag diniscruz/sg-send-vault:latest registry.heroku.com/my-sg-send/web
docker push registry.heroku.com/my-sg-send/web
heroku container:release web -a my-sg-send
heroku config:set SEND__STORAGE_MODE=memory SGRAPH_SEND__ACCESS_TOKEN=<your-key> -a my-sg-send
```

**Heroku's filesystem is ephemeral** — `disk` mode is never valid here; use `memory`
(ephemeral by design) or `s3` (durable).
