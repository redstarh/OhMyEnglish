#!/bin/zsh
# OhMyEnglish 실행 아이콘(.app 번들)을 만든다 (`TASK-291`).
#
# 결과: ~/Applications/OhMyEnglish.app — 누르면 이 리포의 scripts/launcher/launch.sh 를 실행함.
# 바탕화면에는 그 앱의 별칭을 둠. 다시 돌리면 번들을 새로 만듦(별칭은 그대로 씀).
# 아이콘은 icon.svg 를 헤드리스 Chrome 으로 1024px PNG 로 그린 뒤 iconutil 로 묶음.

set -eu

HERE="${0:A:h}"
APP="$HOME/Applications/OhMyEnglish.app"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# ── 아이콘 ──
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --default-background-color=00000000 \
  --window-size=1024,1024 --user-data-dir="$WORK/chrome" \
  --screenshot="$WORK/icon-1024.png" "file://$HERE/icon.svg" >/dev/null 2>&1
mkdir -p "$WORK/AppIcon.iconset"
for size in 16 32 128 256 512; do
  sips -z $size $size "$WORK/icon-1024.png" --out "$WORK/AppIcon.iconset/icon_${size}x${size}.png" >/dev/null
  double=$(( size * 2 ))
  sips -z $double $double "$WORK/icon-1024.png" --out "$WORK/AppIcon.iconset/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$WORK/AppIcon.iconset" -o "$WORK/AppIcon.icns"

# ── 번들 ──
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$WORK/AppIcon.icns" "$APP/Contents/Resources/AppIcon.icns"
cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>OhMyEnglish</string>
  <key>CFBundleDisplayName</key><string>OhMyEnglish</string>
  <key>CFBundleIdentifier</key><string>local.ohmyenglish.launcher</string>
  <key>CFBundleExecutable</key><string>OhMyEnglish</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSMinimumSystemVersion</key><string>13.0</string>
</dict>
</plist>
PLIST
cat > "$APP/Contents/MacOS/OhMyEnglish" <<EXEC
#!/bin/zsh
exec "$HERE/launch.sh"
EXEC
chmod +x "$APP/Contents/MacOS/OhMyEnglish" "$HERE/launch.sh"
touch "$APP"

# ── 바탕화면 별칭 ──
if [[ ! -e "$HOME/Desktop/OhMyEnglish.app" ]]; then
  osascript -e "tell application \"Finder\" to make alias file to POSIX file \"$APP\" at POSIX file \"$HOME/Desktop\"" >/dev/null
fi
echo "만듦: $APP"
