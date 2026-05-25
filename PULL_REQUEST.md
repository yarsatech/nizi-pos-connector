# Pull Request: macOS optimizations, UI updates, and integrated log panel

This pull request introduces several important updates, styling improvements, and platform integrations for the Nizi POS Connector desktop application. 

Here is a summary of the main changes included in this branch:

## 1. macOS integrations
* **Foreground Focus**: Status menu apps on macOS do not automatically bring their window to the front when opened. We solved this by calling a simple AppleScript command when the window triggers:
  `osascript -e 'tell application "System Events" to set frontmost of every process whose name is "NiziPOSConnector" to true'`
  This ensures that text inputs and buttons accept keyboard inputs immediately.
* **Auto-Sizing Window**: The window height is now calculated dynamically on launch based on the size of the internal controls. This ensures no unnecessary scrollbars are rendered.
* **Tray Menu Fix**: On macOS, standard status menu actions trigger both left-click events and the native context menu. We added a check to prevent duplicate menu overlaps.

## 2. UI layout and custom styling
* **Buttons**: Relocated the Connect Now button inside the status card. Added a Quit button at the bottom right of the window footer, styled with a clean borderless look.
* **Dropdowns**: Standard combobox lists look dated and ignore padding. We updated all dropdown widgets to use list views (`QListView`), which allows them to inherit custom spacing and hover effects. We also added a custom styling theme for dropdown items including red highlights for selected states.

## 3. Dedicated uploads page
* **The Problem**: The old image page was confusing because it combined permanent wallpaper slots and real-time temporary image tests in a single place.
* **The Solution**: Created a new page called Upload Images divided into two clear sections:
  * **Wallpaper Image**: Targets permanent memory slots (IMG1 or IMG2) and saves the image to the device.
  * **Temporary Image**: Used for quick real-time testing on the device screen.
  * Both sections now include a visual preview box that displays the selected image scaled to fit. We also deleted the old redundant idle images page.

## 4. Integrated log console
* **Log Section**: Added a diagnostic panel at the bottom of the Device Config page.
* **Open Log**: Opens the app.log file in your system's default text editor.
* **Refresh Logs**: Reads and displays the last 50 log lines directly inside a monospace text field. The logs refresh automatically when the window opens.

## 5. Formatting confirmation
* Added a warning dialog when clicking the Format button. The confirmation button is colored in red to indicate a high-risk action, and the default focus is set to Cancel to prevent accidental keyboard triggers.

---

## Technical changes

* **theme_support.py**: Updated type annotations for compatibility and added dark theme styles for the new image preview and log display widgets.
* **tray_app.py**: Added platform checks to handle tray clicks correctly on macOS.
* **ui_app.py**: Restructured the layout, added the split uploads page, integrated the log viewer panel, implemented window sizing and focus routines, and added the format safety check.
* **web_server.py**: Updated type annotations.

---

## How to test the changes

### macOS focus and sizing
1. Open the application on macOS.
2. Confirm the window height adjusts cleanly to fit all controls.
3. Open another application, click the Nizi tray icon, and verify that the window automatically gains active focus.

### Uploads and image previews
1. Go to the Upload Images page.
2. Select a JPEG image for either Wallpaper or Temporary Image.
3. Verify that a scaled preview of the image is shown immediately inside the preview box.
4. Click upload and verify that the device updates successfully.

### Application logs
1. Open the Device Config page.
2. Verify that you can see the latest log entries in the log box.
3. Click Open Log File and confirm that your system's default editor opens the file.
4. Click Refresh Logs to reload the log entries.

### Format confirmation
1. Go to the Quick Actions page.
2. Click Format.
3. Verify that the warning modal is shown, and that pressing Enter does not trigger formatting (Cancel should be default).
