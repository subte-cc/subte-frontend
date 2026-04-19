# subte.cc client for Windows
*Last Update: 17/04/2026*

### Download [here](https://codeberg.org/subte-cc/subteccwindows/releases)
*Works on Windows 7 onwards, requires [.NET Framework 4.7.2](https://go.microsoft.com/fwlink/?linkid=863265)*

## Domains Tab
![Domains Page](assets/img/docs/win_domains.png "Domains Page")

This page shows a 5 input fields for each domain to be updated. With a manual update button for testing.

## Settings

Here you can tweak the behaviour of the program.

![Settings Page](assets/img/docs/win_settings.png "Settings Page")

The main elements are:

- Token: The API access token provided on the [dashboard](/dashboard).
- Autostart: Enables subte.cc to start upon user logon.
- Auto-Update: Makes domains update automatically after certain time period.
- Auto-Update every: Sets the time in minutes to wait until next update.
- Notifications: Enables notifications indicating update and program status.

## Notifications

Notifications on the notification tray area indicate the update and program status, the main notifications are:

### Subte.cc is now running in the background

Shown when program is minimized with Autostart ON or when it started on user logon.

![Background Notification](assets/img/docs/win_background.png "Background Notification")

### Domains have updated successfully

Shown when domains set on the domain tab have been updated successfully.

![Success Notification](assets/img/docs/win_success.png "Success Notification")

### An error ocurred

If there was an error during the domain update proccess, detailed information about the error is shown.

![Error Notification](assets/img/docs/win_error.png "Error Notification")

*Error 401 (Unauthorized), usually caused when user is making updates too quickly*