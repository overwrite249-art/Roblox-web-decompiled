# stock/

`scripts/fetch_stock.sh` puts Roblox's original files here; `scripts/decompile.sh` runs it automatically. The files are git-ignored because they're Roblox's proprietary code.

| File | Size | sha256 | Source |
|---|---|---|---|
| `WebClient.wasm` | 100,515,451 bytes | `d72c52618f5c153c9b17a97e644914d43918c7122d754d96f79e8323acc6a15d` | https://setup.rbxcdn.com/webclient/version-75f1039cb4964863-RobloxWebClient/WebClient.wasm |
| `WebClient.js` | 128,775 bytes | `81e38a0d9ff71728bb2c04ff578bd71ba720c0a72ff94b78e55f8356042d1228` | https://setup.rbxcdn.com/webclient/version-75f1039cb4964863-RobloxWebClient/WebClient.js |

`WebClient.js` is the Emscripten loader from the same build. It's kept for reference only; no script needs it.
