## Public DownKit Android source transformation

The numbered Base64 fragments in this directory are reassembled by GitHub Actions into a deterministic Python source transformation. The workflow applies this transformation to the pinned public Android source archive, compiles it, signs the ARM64 APK with repository-protected Release secrets, and publishes both the APK and the complete transformed Android Studio project.

The transformation includes the user-facing UI, two-column format picker only, responsive URL entry, navigation state restoration, GitHub Releases updater, actual yt-dlp container/extension display, fragment-aware stream progress, FFmpeg merge statistics, and per-file save progress. It deliberately leaves the settings page in a single-column layout.

The source archive attached to the release is the complete, directly buildable Android Studio project. Signing material is not stored in this directory or in the public source archive.
