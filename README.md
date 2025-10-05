# μ-pki: a handy tool for managing your own pki

## quickstart

First, download or `git clone` this repo, and make sure `uv` has been installed.

Copy `./.env.example` to `./.env`, and replace the example `ENC_KEY` as well as other fields with your own values.

The key could be generated using the following command:

```sh
openssl rand -base64 16
```

```text
% - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - %
|       !!! Remember to keep this file safely and securely. !!!       |
% - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - %
```

Review, and modify if necessary, the preferences `./mu_pki/globals.py`.

Then install dependencies with:

```sh
uv sync
```

Finally, run with:

```sh
./.venv/Scripts/activate # if on windows
./.venv/bin/activate # if otherwise
python -OO -m mu_pki # `-OO` is only for optimization
```
