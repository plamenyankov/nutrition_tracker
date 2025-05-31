# Voice Input Feature Guide

## Overview
The AI Assistant includes voice input functionality to make food logging easier and more convenient. However, implementation varies by device due to browser limitations.

## Desktop (Chrome, Edge, Safari on macOS)
- **Full Support**: Click the "Voice Input" button to start recording
- **Visual Feedback**: Button turns red with pulsing animation while recording
- **Real-time Transcription**: See your words appear as you speak
- **Continuous Recording**: Keeps recording until you click "Stop"
- **Smart Text Handling**: Appends to existing text with proper formatting

## iOS Devices (iPhone/iPad)
- **Limited Support**: Web Speech API is not supported on iOS Safari
- **Alternative Solution**: Use iOS keyboard's built-in dictation
- **How to Use**:
  1. Tap the text input field to bring up the keyboard
  2. Tap the microphone button on the iOS keyboard
  3. Speak your food items
  4. Tap "Done" when finished
- **Voice Button**: Shows reminder to use keyboard dictation

## Android Devices
- **Full Support**: Works like desktop in Chrome browser
- **Alternative**: Can also use keyboard dictation if preferred

## Tips for Best Results

### Speaking Clearly
- Speak at a normal pace
- Pronounce quantities clearly: "two apples" or "100 grams chicken"
- Pause briefly between items

### Supported Formats
- "2 apples"
- "100 grams of chicken breast"
- "one cup of brown rice"
- "half avocado"
- "3 tablespoons olive oil"

### Common Issues

**iOS: Voice button doesn't work**
- This is expected behavior due to iOS limitations
- Use the keyboard microphone instead
- The app will show instructions when you tap the voice button

**Desktop: No microphone access**
- Check browser permissions
- Allow microphone access when prompted
- Check system settings if issues persist

**Poor recognition accuracy**
- Speak more clearly
- Reduce background noise
- Try shorter phrases
- Check microphone settings

## Technical Details

The voice input feature uses the Web Speech API, which has varying support:
- **Chrome/Edge**: Full support
- **Safari (macOS)**: Full support
- **Safari (iOS)**: Not supported
- **Firefox**: Limited support

For iOS users, the native keyboard dictation provides a seamless alternative that works just as well for entering food items.
