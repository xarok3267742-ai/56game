# Signing Certificate Report

Checked on 6 June 2026.

## Release Artifact

- Signed AAB: `app/build/outputs/bundle/release/app-release.aab`
- Package: `com.qgrid.mobile`
- Version: `1.0.0` (`versionCode = 1`)
- Signing purpose: local upload key for Play Console upload/app signing enrollment.

## Upload Key Certificate

- Keystore type: PKCS12
- Key alias: `qgrid_upload`
- Certificate owner: `CN=QuietGrid Upload, OU=QuietGrid, O=QuietGrid, L=Local, ST=Local, C=US`
- Certificate issuer: `CN=QuietGrid Upload, OU=QuietGrid, O=QuietGrid, L=Local, ST=Local, C=US`
- Serial number: `719e6a96be867b6d`
- Valid from: `2026-06-02 12:19:09 MSK`
- Valid until: `2053-10-18 12:19:09 MSK`
- SHA-1 fingerprint: `8F:A1:31:EE:7D:2B:FB:22:C6:F8:67:E7:28:39:AF:92:2B:18:8D:41`
- SHA-256 fingerprint: `DD:97:1E:77:8A:0A:87:E7:9E:1A:44:18:1D:45:3B:83:80:7F:B3:06:FF:48:DE:AC:BA:FD:48:11:36:83:72:F1`
- Signature algorithm: `SHA384withRSA`

## Verification Commands

Use the local ignored signing files to reproduce the certificate report. Do not paste credentials into shared logs.

```bash
keytool -list -v -keystore private/signing/qgrid-upload.p12 -storetype PKCS12 -alias qgrid_upload
```

```bash
jarsigner -verify -verbose -certs app/build/outputs/bundle/release/app-release.aab
```

## Security Notes

- This report contains public certificate metadata only.
- The keystore file remains `private/signing/qgrid-upload.p12`.
- The local credential file remains `keystore.properties`.
- Local `local.properties`, `keystore.properties`, `private/signing/*.p12`, common signing-key extensions (`*.jks`, `*.keystore`, `*.pem`, `*.pk8`, `*.key`) and Android upload/install artifact extensions (`*.apk`, `*.aab`, `*.apks`, `*.idsig`) are ignored case-insensitively by `.gitignore`; `tools/verify_release.py` verifies representative lower/upper-case paths with `git check-ignore`, and the active local signing files currently have owner-only filesystem permissions.
- `tools/verify_release.py` compares this report with `keytool -printcert -jarfile app/build/outputs/bundle/release/app-release.aab` so the documented certificate cannot drift from the signed AAB.
- `tools/verify_release.py` also checks local `local.properties`, `keystore.properties` and `private/signing/*.p12` permissions, and checks `keystore.properties`, when present, for `private/signing/qgrid-upload.p12` and `keyAlias=qgrid_upload`.
- Back up the keystore and credentials in an owner-controlled secure location before Play Console upload.
- Never upload this report as a Play store asset; it is a release handoff/reference file.
