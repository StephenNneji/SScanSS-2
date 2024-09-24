#!/bin/bash

SSCANSS_PATH="../bundle/app/sscanss.app"
EDITOR_PATH="../bundle/editor.app"
VER=$1
DEV_TEAM_ID=$2
API_CONNECT_ISSUER=$3
API_CONNECT_KEY_ID=$4

# Sign code
codesign -v --deep --force --options=runtime --entitlements ./entitlements.plist --sign ${DEV_TEAM_ID} --timestamp ${EDITOR_PATH}/Contents/Resources/*.dylib
codesign -v --deep --force --options=runtime --entitlements ./entitlements.plist --sign ${DEV_TEAM_ID} --timestamp ${EDITOR_PATH}
codesign -v --deep --force --options=runtime --entitlements ./entitlements.plist --sign ${DEV_TEAM_ID} --timestamp ${SSCANSS_PATH}/Contents/Resources/*.dylib
codesign -v --deep --force --options=runtime --entitlements ./entitlements.plist --sign ${DEV_TEAM_ID} --timestamp ${SSCANSS_PATH}

# Build Pkg
sed -e 's/@VERSION@/${Ver}/g' distribution.xml.in > distribution.xml
pkgbuild --root ${EDITOR_PATH} --identifier com.sscanss2.editor.pkg --version ${VER} --install-location "/Applications/sscanss-editor.app" editor.pkg
pkgbuild --root ${SSCANSS_PATH} --identifier com.sscanss2.sscanss.pkg --version ${VER} --install-location "/Applications/sscanss.app" sscanss.pkg
productbuild --sign ${DEV_TEAM_ID} --timestamp --distribution distribution.xml --resources . sscanss2.pkg

# Notarise and staple
xcrun notarytool submit --issuer ${API_CONNECT_ISSUER} --key-id ${API_CONNECT_KEY_ID} --key ./auth_key.p8 --wait sscanss2.pkg 
xcrun stapler staple sscanss2.pkg
