# FOLIUX Android App Builder

I have prepared this folder so you can generate your Android app (.apk) in just a few clicks from your own computer.

### Why build it on your machine?
Android apps must be "signed" or "built" using specific tools (Node.js and Android SDK) that are not available on this web server. Building it locally ensures you have the actual APK file to share or upload.

### Instructions:

1.  **Prerequisites**:
    *   Install **Node.js** (from [nodejs.org](https://nodejs.org/))
    *   Install **Java JDK 11** or newer.

2.  **Generate the App**:
    *   Download this `twa_builder` folder to your computer.
    *   Double-click **`make_apk.bat`**.
    *   The script will install the necessary tools and generate an **unsigned APK**.

3.  **To make it "Official" (Verified)**:
    *   Once you have your SHA-256 fingerprint from the build process, update the fingerprint in `core/views.py` (the `assetlinks_json` function).
    *   This will remove the browser address bar from the top of the app.
