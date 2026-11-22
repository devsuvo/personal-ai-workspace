# macOS Production Build Guide (v1.0.0)

Because macOS `.app` bundles, `iconutil`, and `hdiutil` `.dmg` images require macOS tooling, run this build directly on your MacBook (Apple Silicon `arm64` or Intel `x86_64`).

## Prerequisites (MacBook)

- macOS 13+ (Ventura, Sonoma, or Sequoia)
- Xcode Command Line Tools (`xcode-select --install`)
- Python 3.12+
- Node.js 20+

## Build `.app` Bundle and `.dmg` Installer

```bash
chmod +x packaging/macos/build_macos.sh
./packaging/macos/build_macos.sh
```

Outputs:
- `dist/macos/PersonalAIWorkspace.app`
- `dist/macos/PersonalAIWorkspace-1.0.0-<arch>.dmg`

User data persists independently on your Mac at:
`~/Library/Application Support/PersonalAIWorkspace/storage/`

## Code Signing & Apple Notarization (Optional for Distribution)

If you distribute the `.dmg` beyond your own MacBook, macOS Gatekeeper requires an Apple Developer ID Application certificate:

```bash
# 1. Sign the .app bundle with Hardened Runtime
codesign --deep --force --options runtime \
  --sign "Developer ID Application: YOUR NAME (TEAM_ID)" \
  dist/macos/PersonalAIWorkspace.app

# 2. Recreate and sign the DMG
codesign --force --sign "Developer ID Application: YOUR NAME (TEAM_ID)" \
  dist/macos/PersonalAIWorkspace-1.0.0-arm64.dmg

# 3. Submit for notarization & staple
xcrun notarytool submit dist/macos/PersonalAIWorkspace-1.0.0-arm64.dmg \
  --apple-id "you@example.com" --team-id "TEAM_ID" --password "@keychain:AC_PASSWORD" --wait
xcrun stapler staple dist/macos/PersonalAIWorkspace-1.0.0-arm64.dmg
```

For personal use on your own Mac without a paid Apple Developer certificate, right-click `PersonalAIWorkspace.app` → **Open** on first launch to approve it locally.
