## Setup

- Clone / download this repository.
- Open the sample project in XCode.
- Make sure you have a valid API key. You can request one for your Empatica Connect account from our [Developer Area][1].
- Edit `ViewController.swift` and assign your API key to the `EMPATICA_API_KEY` constant .
- Download the E4link.framework iOS SDK from our [Developer Area][1].
- Copy the file to the 'Libs' folder
- Build and Run the project.
- If a device is in range and its light is blinking green, but the app doesn't connect, please check that the discovered device can be used with your API key. If the `allowed` parameter is always false, the device is not linked to your API key. Please check your [Developer Area][1].

If you need any additional information about the Empatica API for iOS, please check the [Official Documentation][2].

[1]: https://www.empatica.com/connect/developer.php
[2]: http://developer.empatica.com
