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

echo "Built $APP"
