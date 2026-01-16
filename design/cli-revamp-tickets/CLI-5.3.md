# Add Template Download Progress Indicator

## Description

Add a visual progress indicator during template downloads to provide feedback to users, especially for larger templates like the full baseboards template (12 MB). This improves the user experience by showing that the CLI is actively working and provides an estimate of completion.

The progress indicator should:
- Show download progress as a percentage
- Display current and total file size
- Show download speed
- Use a spinner or progress bar
- Update in real-time

## Dependencies

- CLI-2.5 (Template downloader must exist)

## Files to Create/Modify

- Modify `/packages/cli-launcher/src/utils/template-downloader.ts`

## Testing

### Progress Display Test
```bash
# Clear cache to force download
rm -rf ~/.baseboards/templates/*

# Download large template
baseboards up test --template baseboards

# Expected output:
# Downloading template baseboards...
# ████████████████████░░ 80% (9.6 MB / 12.0 MB) [1.2 MB/s]
# Template downloaded successfully
```

### Small Template Test
```bash
# Download small template (basic)
baseboards up test --template basic

# Expected output:
# Downloading template basic...
# ████████████████████████ 100% (45 KB / 45 KB) [800 KB/s]
# Template downloaded successfully
```

### Cache Hit Test
```bash
# First download (shows progress)
baseboards up test1 --template baseboards

# Second download (no progress, uses cache)
baseboards up test2 --template baseboards

# Expected: No "Downloading..." message on second run
# Or: "Using cached template..." message
```

### Network Speed Test
```bash
# Test with slow network (can be simulated)
# Progress bar should update smoothly
# Speed should be calculated and displayed
```

## Acceptance Criteria

### Progress Library

- [ ] Use progress library (ora, cli-progress, or similar):
  ```typescript
  import ora from "ora"; // OR
  import cliProgress from "cli-progress";
  ```

- [ ] Add dependency to package.json if not already present

### Download Function Updates

- [ ] Update `downloadTemplate()` to show progress:
  ```typescript
  export async function downloadTemplate(
    name: string,
    version: string,
    targetDir: string
  ): Promise<void> {
    // Check cache first
    const cached = await getCachedTemplate(name, version);
    if (cached) {
      console.log(`Using cached template ${name}...`);
      await extractTemplate(cached, targetDir);
      return;
    }

    // Fetch manifest
    const manifest = await fetchTemplateManifest(version);
    const template = manifest.templates.find(t => t.name === name);

    if (!template) {
      throw new Error(`Template '${name}' not found`);
    }

    // Start progress
    console.log(`\nDownloading template ${name}...`);
    const spinner = ora().start();

    try {
      // Download with progress
      const tempPath = await downloadWithProgress(template, spinner);

      // Verify checksum
      spinner.text = "Verifying download...";
      await verifyChecksum(tempPath, template.checksum);

      // Cache and extract
      spinner.text = "Extracting template...";
      await cacheTemplate(tempPath, name, version);
      await extractTemplate(tempPath, targetDir);

      spinner.succeed("Template downloaded successfully");
    } catch (error) {
      spinner.fail("Download failed");
      throw error;
    }
  }
  ```

### Progress Implementation

- [ ] Implement `downloadWithProgress()` function:
  ```typescript
  async function downloadWithProgress(
    template: TemplateInfo,
    spinner: Ora
  ): Promise<string> {
    const url = `https://github.com/weirdfingers/boards/releases/download/v${version}/${template.file}`;
    const tempPath = path.join(os.tmpdir(), template.file);

    const response = await axios.get(url, {
      responseType: "stream",
      onDownloadProgress: (progressEvent) => {
        const total = progressEvent.total || template.size;
        const current = progressEvent.loaded;
        const percent = Math.round((current / total) * 100);
        const currentMB = (current / 1024 / 1024).toFixed(1);
        const totalMB = (total / 1024 / 1024).toFixed(1);

        spinner.text = `${percent}% (${currentMB} MB / ${totalMB} MB)`;
      },
    });

    // Write stream to file
    const writer = fs.createWriteStream(tempPath);
    response.data.pipe(writer);

    return new Promise((resolve, reject) => {
      writer.on("finish", () => resolve(tempPath));
      writer.on("error", reject);
    });
  }
  ```

### Display Stages

- [ ] Show different stages:
  - [ ] "Downloading template {name}..."
  - [ ] Progress updates during download
  - [ ] "Verifying download..."
  - [ ] "Extracting template..."
  - [ ] "Template downloaded successfully" (green checkmark)

### Size Formatting

- [ ] Human-readable sizes:
  ```typescript
  function formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }
  ```

### Speed Calculation (Optional)

- [ ] Calculate and display download speed:
  ```typescript
  let lastTime = Date.now();
  let lastLoaded = 0;

  onDownloadProgress: (progressEvent) => {
    const now = Date.now();
    const timeDiff = (now - lastTime) / 1000; // seconds
    const loadedDiff = progressEvent.loaded - lastLoaded;
    const speed = loadedDiff / timeDiff; // bytes per second

    const speedStr = formatBytes(speed) + "/s";
    spinner.text = `${percent}% (${currentMB} MB / ${totalMB} MB) [${speedStr}]`;

    lastTime = now;
    lastLoaded = progressEvent.loaded;
  }
  ```

### Cache Behavior

- [ ] When cache hit, show:
  ```
  Using cached template baseboards...
  Extracting template...
  ✓ Template ready
  ```

- [ ] No progress bar on cache hit (extraction is fast)

### Error Handling

- [ ] Download interruption handled:
  - Show: "✗ Download failed"
  - Clean up partial files
  - Show helpful error message

- [ ] Network timeout handled
- [ ] Disk full handled

### Quality

- [ ] Progress updates smooth (not too frequent, not too slow)
- [ ] Terminal not overwhelmed with updates
- [ ] Progress bar/spinner clears properly on completion
- [ ] No flickering or rendering issues

### Testing

- [ ] Large template shows progress (baseboards ~12 MB)
- [ ] Small template shows progress (basic ~45 KB)
- [ ] Cache hit shows appropriate message
- [ ] Network errors handled gracefully
- [ ] Progress bar clears on completion
- [ ] Works in CI/CD environments (non-TTY)

### CI/CD Compatibility

- [ ] Detect non-TTY environment:
  ```typescript
  const isInteractive = process.stdout.isTTY;

  if (!isInteractive) {
    console.log(`Downloading template ${name}...`);
    // No spinner, just plain messages
  } else {
    // Use spinner/progress bar
  }
  ```
