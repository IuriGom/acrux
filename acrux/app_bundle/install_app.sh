#!/bin/bash
# Build and install the native Swift Acrux.app to the user's Applications folder.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SWIFT_DIR="${1:-$SCRIPT_DIR/../../swift_app/Acrux}"
APP_DST="${2:-$HOME/Applications/Acrux.app}"

if [ ! -f "$SWIFT_DIR/build_app.sh" ]; then
    echo "error: build_app.sh not found in $SWIFT_DIR" >&2
    exit 1
fi

echo "Building native Swift Acrux.app..."
cd "$SWIFT_DIR"
./build_app.sh

echo "Installing to $APP_DST..."
rm -rf "$APP_DST"
cp -R "$SWIFT_DIR/.build/release/Acrux.app" "$APP_DST"
xattr -cr "$APP_DST"

echo "Acrux.app installed to $APP_DST"
echo "Drag it to your Dock or right-click > Options > Keep in Dock."
echo "First launch: right-click the app and choose Open to bypass Gatekeeper."
