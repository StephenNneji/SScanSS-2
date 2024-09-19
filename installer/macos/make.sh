#!/bin/bash

DEV_TEAM_ID=$1
SSCANSS_PATH="../bundle/app/sscanss.app"
EDITOR_PATH="../bundle/editor.app"


# Sign code
codesign -v --deep --force --options=runtime --entitlements ./entitlements.plist --sign ${DEV_TEAM_ID} --timestamp ${EDITOR_PATH}/Contents/Resources/*.dylib

codesign -v --deep --force --options=runtime --entitlements ./entitlements.plist --sign ${DEV_TEAM_ID} --timestamp ${EDITOR_PATH}

codesign -v --deep --force --options=runtime --entitlements ./entitlements.plist --sign ${DEV_TEAM_ID} --timestamp ${SSCANSS_PATH}/Contents/Resources/*.dylib

codesign -v --deep --force --options=runtime --entitlements ./entitlements.plist --sign ${DEV_TEAM_ID} --timestamp ${SSCANSS_PATH}

# Build Pkg
pkgbuild --root ${EDITOR_PATH} --identifier com.sscanss2.editor.pkg \
 --version "2.2.0" --min-os-version 10.9 --install-location "/Applications/editor.app" editor.pkg

pkgbuild --root ${SSCANSS_PATH} --identifier "com.sscanss2.sscanss.pkg"  \
--version "2.2.0" --min-os-version 10.9 --install-location "/Applications/sscanss.app" sscanss.pkg

productbuild --sign ${DEV_TEAM_ID} --timestamp --distribution distribution.xml --resources . sscanss2.pkg

# Notarise and staple
#echo -n $API_CONNECT_KEY | base64 -d -o  ./auth_key.p8
#xcrun notarytool submit --issuer $API_CONNECT_ISSUER --key-id $API_CONNECT_KEY_ID --key ./#auth_key.p8 --wait sscanss2.pkg 
#xcrun stapler staple sscanss2.pkg
