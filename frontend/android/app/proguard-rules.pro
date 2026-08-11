# Add project specific ProGuard rules here.
# By default, the flags in this file are appended to flags specified
# in /usr/local/Cellar/android-sdk/24.3.3/tools/proguard/proguard-android.txt
# You can edit the include path and order by changing the proguardFiles
# directive in build.gradle.
#
# For more details, see
#   http://developer.android.com/guide/developing/tools/proguard.html

# Add any project specific keep options here:

# ---------------------------------------------------------------------------
# LiveKit / WebRTC.
#
# Inert today: enableProguardInReleaseBuilds is false in app/build.gradle. Kept
# here because the failure mode when someone flips it is nasty and one-sided --
# WebRTC reaches its native layer through JNI and reflection, so R8 sees the
# Java classes as unreferenced and removes them. Debug keeps working, release
# builds fail at the moment a candidate joins an interview, and the stack trace
# names a missing class rather than the shrinker.
-keep class org.webrtc.** { *; }
-keep class com.oney.WebRTCModule.** { *; }
-keep class io.livekit.** { *; }
-keep class com.livekit.** { *; }
-dontwarn org.webrtc.**

# The recorder is a Nitro module, which resolves its JNI entry points the same
# way and breaks the same way.
-keep class com.margelo.nitro.** { *; }
