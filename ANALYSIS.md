# Fluxer Repo Analysis

## Monorepo structure (top-level)

- `fluxer_app`: React web client (Rspack build/dev, LiveKit integration).
- `fluxer_desktop`: Electron desktop client.
- `fluxer_admin`: Admin UI/service.
- `fluxer_marketing`: Marketing site.
- `fluxer_docs`: Documentation site (Mint).
- `fluxer_api`: TypeScript HTTP API service (Hono-based).
- `fluxer_server`: Umbrella server for self-hosters; composes multiple backend services.
- `fluxer_gateway`: Erlang/OTP WebSocket gateway for real-time messaging/presence.
- `fluxer_relay`: Erlang relay service.
- `fluxer_relay_directory`: TypeScript service for relay discovery/directory.
- `fluxer_app_proxy`: App proxy service for serving/proxying the web client.
- `fluxer_media_proxy`: Media proxy service.
- `packages/*`: Shared libraries used across apps/services (config, schema, ui, api, utils, etc.).
- `fluxer_static`: Static CDN payload (images, emoji, fonts, web icons, and `libs/` like MediaPipe).
- `fluxer_devops`: Deployment helpers (e.g., LiveKit bootstrapper).
- `fluxer_integration`: Integration test harness/scripts.

Other repo-level directories:
- `config`: Default configs and config templates.
- `dev`: Development helpers (local tooling/scripts).
- `media`: Repo media (README images, showcase, etc.).
- `patches`: pnpm patch files for vendored dependency fixes.
- `scripts`: Repo-wide scripts (dev bootstrap, CI helpers, etc.).
- `tsconfigs`: Shared TS config packages.

## Findings (iterative)

1. Git LFS is configured only for `fluxer_static/**` via `.gitattributes`. All files under `fluxer_static` are LFS pointers in this checkout (e.g., `fluxer_static/marketing/branding/logo-color.svg`), so the static asset tree is currently missing its real content.

2. The `fluxer_static` tree contains CDN assets (avatars, badges, emojis, fonts, marketing images, web icons, and libs). The app defaults to the public CDN `https://fluxerstatic.com` for these assets, so missing LFS content primarily affects self-hosting or local static CDN setups, not core runtime if the public CDN is reachable.

3. The only `.wasm` files in `fluxer_static` are MediaPipe Tasks Vision binaries:
   - `fluxer_static/libs/mediapipe/tasks-vision/0.10.14/wasm/vision_wasm_internal.wasm`
   - `fluxer_static/libs/mediapipe/tasks-vision/0.10.14/wasm/vision_wasm_nosimd_internal.wasm`
   These are referenced by the client for background blur/virtual background processing in video calls.

4. The client references MediaPipe assets on the static CDN (`https://fluxerstatic.com/...`) for video background processing (segmentation model and wasm). Missing LFS content would break background blur / virtual background when self-hosting the static CDN, but should not affect core chat or voice signaling if the CDN is reachable.

5. The repo is a monorepo (pnpm + turbo) with multiple apps and services:
   - `fluxer_app`: React web client (build/dev scripts, Rspack).
   - `fluxer_desktop`: Electron desktop client.
   - `fluxer_api`: TypeScript HTTP API service.
   - `fluxer_server`: Umbrella server for self-hosters that wires together multiple backend services.
   - `fluxer_gateway`: Erlang/OTP WebSocket gateway (real-time messaging/presence).
   - `fluxer_relay`: Erlang relay service (rebar config present).
   - `fluxer_relay_directory`: TypeScript service (package.json present).
   - `fluxer_app_proxy`: App proxy service for serving/proxying the web client.
   - `fluxer_media_proxy`: Media proxy service.
   - `fluxer_admin`: Admin UI/service.
   - `fluxer_marketing`: Marketing site.
   - `fluxer_docs`: Documentation site.
   - `packages/*`: Shared libraries (config, schema, ui, api, etc.) used by the apps/services.

6. Outside `fluxer_static`, the only `.wasm` file is a test fixture: `fluxer_app/src/test/LibfluxcoreMock.wasm`. There are no other runtime wasm binaries in the repo.

7. `fluxer_static` is the static CDN payload (avatars, badges, emojis, embeds, fonts, marketing assets, web icons, and `libs/` like MediaPipe). It appears intended to back `https://fluxerstatic.com` or a self-hosted `static_cdn_domain` config.
