#!/bin/bash
# Build the native Swift Acrux.app.

set -e

cd "$(dirname "$0")"

echo "Building Acrux with Swift..."
swift build -c release

APP=".build/release/Acrux.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"
mkdir -p "$APP/Contents/Resources"

cp .build/release/Acrux "$APP/Contents/MacOS/Acrux"
cp Info.plist "$APP/Contents/Info.plist"
cp Resources/Acrux.icns "$APP/Contents/Resources/Acrux.icns"

chmod +x "$APP/Contents/MacOS/Acrux"

# Sign with a stable self-signed identity when available so macOS privacy
# (TCC) grants survive rebuilds. Ad-hoc signatures change every build and
# silently revoke the app's folder access. Create the identity once with:
#   openssl req -x509 -newkey rsa:2048 -keyout k.pem -out c.pem -days 3650 \
#     -nodes -subj "/CN=Acrux Dev" -addext "extendedKeyUsage=codeSigning"
#   openssl pkcs12 -export -out acrux_dev.p12 -inkey k.pem -in c.pem
#   security import acrux_dev.p12 -k ~/Library/Keychains/login.keychain-db -T /usr/bin/codesign
if security find-certificate -c "Acrux Dev" ~/Library/Keychains/login.keychain-db >/dev/null 2>&1; then
    codesign --force --sign "Acrux Dev" "$APP"
    echo "Signed with 'Acrux Dev' identity."
else
    echo "WARNING: 'Acrux Dev' identity not found; app left ad-hoc signed (TCC grants will not persist)."
fi

echo "Built $APP"
