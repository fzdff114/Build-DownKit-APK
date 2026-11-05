## Public release patch bundle

The numbered `.b64` fragments in this folder are a compressed, deterministic source transformation used by the GitHub Actions release workflow.

The workflow:
1. Checks out the original DownKit Android source archive.
2. Reassembles and validates the patch bundle.
3. Applies the public app UI, navigation-state, update-check, progress-stage and task-queue changes.
4. Builds the ARM64 Android package and publishes the complete resulting Android Studio project as a source ZIP in GitHub Releases.

The reconstructed source is included in each public release as `DownKit-Android-<version>-source.zip`. No signing key or signing password is stored in this folder.
