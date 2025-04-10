# Camera Functionality

This document explains how to use and troubleshoot the camera functionality in the Journal App.

## How It Works

The "Take Photo" button uses your device's camera to capture images and add them to your journal entries. This feature uses the browser's MediaDevices API, which has specific security requirements.

## Common Issues

### Camera Not Working on Remote Server

If the camera works when accessing the app on localhost (127.0.0.1) but not when accessing it from another IP address (like 192.168.1.135), this is due to browser security requirements.

**Why**: For security reasons, modern browsers only allow camera access in secure contexts:
- Localhost (127.0.0.1) connections are automatically considered secure
- Remote IP addresses require HTTPS (SSL/TLS) connections

### Solution: Enable HTTPS

To enable the camera when accessing from a remote IP address, you need to run the app with HTTPS:

1. Install the required package:
   ```
   pip install pyopenssl
   ```

2. Edit app.py and uncomment the SSL line:
   ```python
   # Change this:
   app.run(host="0.0.0.0", debug=True)
   
   # To this (remove the # at the beginning):
   app.run(host="0.0.0.0", debug=True, ssl_context='adhoc')
   ```

3. Restart the app and access it using https:// instead of http://

4. Accept the self-signed certificate warning in your browser

## For Production Use

For production environments, use proper SSL certificates:

1. Obtain SSL certificates (cert.pem and key.pem)
2. Update app.py:
   ```python
   app.run(host="0.0.0.0", ssl_context=('cert.pem', 'key.pem'))
   ```

Alternatively, use a reverse proxy like Nginx or Apache with proper SSL certificates.

## Browser Compatibility

The camera functionality is supported in all modern browsers but requires:
- HTTPS (except on localhost)
- Camera permissions granted
- Hardware access to a camera

## Troubleshooting

If you're still having issues:
1. Check browser console for error messages
2. Ensure camera permissions are granted
3. Try accessing on localhost if possible
4. Update to the latest version of your browser