# Zephyr and LVGL version integrity

Read the workspace's `.west/config` and `west list` to identify the manifest project and actual LVGL project name/path. In a workspace where Zephyr is the manifest project it may be named `manifest`, not `zephyr`; `west list zephyr` is not portable. Use Git directly for the manifest repository:

```sh
git -C "$ZEPHYR_BASE" rev-parse HEAD
git -C "$ZEPHYR_BASE" status --short --branch
west list -f '{name} {path} {revision}'
west list lvgl -f '{name} {path} {revision}'
```

For the LVGL checkout path actually reported by West, inspect `git rev-parse HEAD`, `git status --short --branch`, and the relevant manifest-rev (when present). `west list` revision is the manifest declaration; it does not prove the checkout HEAD matches or is clean. Avoid assuming its path or declared revision on other workspaces.

`west manifest --freeze -o manifest.lock.yml` writes a frozen manifest using manifest-rev SHAs, not necessarily each project's current HEAD and not the manifest repository's own working-tree commit. It can fail for uncloned projects or unresolved manifest imports. It does not automatically change the active manifest, guarantee a clean workspace, pin SDK/image/Python, or guarantee all blobs/assets are available. Do not write a lock file without checking status and task scope. Record the manifest repository commit, relevant actual module HEADs/dirty state, resolved manifest, board, SDK, image digest and tool versions; verify a reconstruction in a separate workspace before claiming reproducibility. Check `west manifest --help` for the installed version.

The Zephyr SDK version reference in `SDK_VERSION` and the official compatibility documentation help identify a candidate; match build tools and Python dependencies too, and verify a clean build on the requested target. Reusing a Docker image with matching SDK alone does not prove full compatibility. `west update` changes project checkouts and must be preceded by inspection of local changes.

Official examples are starting points, not universal simulator instructions: inspect version-matched `samples/subsys/display/lvgl` and `samples/modules/lvgl/demos`, their `sample.yaml`/`tests.yaml`, board overlays and the supported display/input backend before selecting build arguments. A `native_sim` build without a working window/display does not validate rendering. Sources: https://docs.zephyrproject.org/latest/develop/west/basics.html and https://docs.zephyrproject.org/latest/develop/application/index.html .
