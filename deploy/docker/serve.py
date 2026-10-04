# Container entrypoint for the sgit vaults API image.
#
# Boots the vault API under uvicorn on $PORT (default 8080). Until phase-1 step 1.3 lands the
# code in this repo, the app is the origin package's User FastAPI app (the same one that runs
# on dev.send.sgraph.ai today). When sgit_vaults is importable, it is used instead — same
# contract, new home. No behaviour is added here: no UI, no extra routes, no auth changes.

import os
import warnings

warnings.filterwarnings('ignore')


def create_app():
    try:
        from sgit_vaults.api.Fast_API__Vaults import Fast_API__Vaults as App          # phase-1 step 1.3 onwards
        source = 'sgit_vaults'
    except ImportError:
        from sgraph_ai_app_send.lambda__user.fast_api.Fast_API__SGraph__App__Send__User import Fast_API__SGraph__App__Send__User as App
        source = 'sgraph_ai_app_send (origin package)'
    with App() as _:
        _.setup()
        app = _.app()
    print(f'[serve] vault API from {source}; storage mode {os.environ.get("SEND__STORAGE_MODE", "(auto)")}')
    return app


def main():
    import uvicorn
    uvicorn.run(create_app(), host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), log_level='info')


if __name__ == '__main__':
    main()
