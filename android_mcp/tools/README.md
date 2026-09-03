# android_mcp tools

## analyze_device_apks.py

Windows/PowerShell friendly static analyzer for APKs collected under:

```powershell
android_mcp\_work\device_apks
```

It scans package-named subdirectories, prefers decoded text `AndroidManifest.xml`
files from apktool/jadx-style output, and falls back to local Android SDK tools
(`aapt`, `aapt2`, `apkanalyzer`) or a conservative ZIP inventory when decoded
manifests are unavailable.

Example:

```powershell
python .\android_mcp\tools\analyze_device_apks.py --pretty
```

If decoded manifests are missing, decode selected pulled APKs first:

```powershell
& ".\tools\jdk-17\bin\java.exe" -jar ".\tools\apktool.jar" d -s -f `
  -o ".\android_mcp\_work\device_apks\com.junge.algorithmAidePro\apktool" `
  ".\android_mcp\_work\device_apks\com.junge.algorithmAidePro\base.apk"
```

Default output:

```powershell
android_mcp\_work\device_apks\analysis_manifest.json
```

The JSON includes package name, APK files, activities/services/receivers/providers,
exported components, authorities, permissions, intent actions, data schemes, and
Xposed-related manifest metadata.
