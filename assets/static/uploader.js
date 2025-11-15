document.addEventListener("DOMContentLoaded", () => {

    const fileInput = document.getElementById("file-upload");
    const filenameLabel = document.getElementById("file-upload-filename");
    const renameInput = document.getElementById("file-rename-input");

    const startBtn = document.getElementById("start-upload-btn");
    const pauseBtn = document.getElementById("pause-upload-btn");

    const progressContainer = document.getElementById("upload-progress-container");
    const progressBar = document.getElementById("upload-progress-bar");
    const statusText = document.getElementById("upload-status-text");
    const percentText = document.getElementById("upload-percentage");

    // ----------------------------
    // UPLOAD SESSION
    // ----------------------------
    let uploadSession = {
        file: null,
        customName: null,
        chunkSize: 10 * 1024 * 1024,
        totalChunks: 0,
        chunksCompleted: 0,
        isPaused: false,
        isMerging: false,
        fileId: null,
        nextChunkToIndex: 0,
        activeConnections: 0,
        maxConcurrency: 4,
        path: ""
    };

    const generateId = () => Math.random().toString(36).substring(2, 10);

    function resetUI() {
        progressContainer.style.display = "none";

        progressBar.style.width = "0%";
        percentText.textContent = "0%";
        statusText.textContent = "Uploading...";

        pauseBtn.style.display = "none";
        pauseBtn.textContent = "Pause";
        pauseBtn.disabled = false;

        startBtn.style.display = "block";
        startBtn.textContent = "Start Upload";

        uploadSession = {
            file: null,
            customName: null,
            chunkSize: 10 * 1024 * 1024,
            totalChunks: 0,
            chunksCompleted: 0,
            isPaused: false,
            isMerging: false,
            fileId: null,
            nextChunkToIndex: 0,
            activeConnections: 0,
            maxConcurrency: 4,
            path: ""
        };
    }

    // ----------------------------
    // FILE INPUT
    // ----------------------------

    fileInput.addEventListener("change", () => {
        const file = fileInput.files[0];
        if (!file) {
            filenameLabel.textContent = "No file chosen";
            renameInput.style.display = "none";
            return;
        }

        filenameLabel.textContent = file.name;
        renameInput.style.display = "block";
        renameInput.value = file.name;
    });

    // ----------------------------
    // START UPLOAD
    // ----------------------------

    startBtn.addEventListener("click", () => {
        if (!fileInput.files.length) {
            alert("Select a file first");
            return;
        }

        const file = fileInput.files[0];

        if (window.maxUploadBytes > 0 && file.size > window.maxUploadBytes) {
            alert(`File too large! Limit = ${Math.round(window.maxUploadBytes / 1024 / 1024)} MB`);
            return;
        }

        uploadSession.file = file;
        uploadSession.customName = renameInput.value.trim() || file.name;
        uploadSession.totalChunks = Math.ceil(file.size / uploadSession.chunkSize);
        uploadSession.fileId = generateId();
        uploadSession.path = window.currentState.path;
        uploadSession.nextChunkToIndex = 0;

        progressContainer.style.display = "block";
        pauseBtn.style.display = "inline-block";
        startBtn.style.display = "none";

        processQueue();
    });

    // ----------------------------
    // CHUNK UPLOAD
    // ----------------------------

    async function uploadChunk(i) {
        uploadSession.activeConnections++;

        const start = i * uploadSession.chunkSize;
        const end = Math.min(start + uploadSession.chunkSize, uploadSession.file.size);
        const chunk = uploadSession.file.slice(start, end);

        const fd = new FormData();
        fd.append("file", chunk);
        fd.append("chunkIndex", i);
        fd.append("totalChunks", uploadSession.totalChunks);
        fd.append("fileId", uploadSession.fileId);
        fd.append("filename", uploadSession.customName);
        fd.append("path", uploadSession.path);
        fd.append("totalSize", uploadSession.file.size);

        try {
            const res = await fetch("/api/upload_chunk", { method: "POST", body: fd });
            const data = await res.json();

            uploadSession.activeConnections--;

            if (!data.success) throw new Error(data.error);

            if (data.merging) {
                uploadSession.isMerging = true;

                progressBar.style.width = "100%";
                percentText.textContent = "100%";
                statusText.textContent = "Merging...";

                pauseBtn.disabled = true;

                // Auto reset after merge
                setTimeout(() => {
                    resetUI();
                }, 1500);

                return;
            }

            uploadSession.chunksCompleted++;
            const pct = Math.floor((uploadSession.chunksCompleted / uploadSession.totalChunks) * 100);

            progressBar.style.width = pct + "%";
            percentText.textContent = pct + "%";

            processQueue();

        } catch (err) {
            console.error(err);
            uploadSession.activeConnections--;

            if (!uploadSession.isPaused) {
                uploadSession.isPaused = true;
                pauseBtn.textContent = "Resume";

                statusText.textContent = "Network Error. Paused";
            }
        }
    }

    function processQueue() {
        if (uploadSession.isPaused || uploadSession.isMerging) return;

        while (
            uploadSession.activeConnections < uploadSession.maxConcurrency &&
            uploadSession.nextChunkToIndex < uploadSession.totalChunks
        ) {
            uploadChunk(uploadSession.nextChunkToIndex);
            uploadSession.nextChunkToIndex++;
        }
    }

    // ----------------------------
    // PAUSE/RESUME
    // ----------------------------

    pauseBtn.addEventListener("click", () => {
        if (!uploadSession.file) return;

        if (uploadSession.isPaused) {
            uploadSession.isPaused = false;
            pauseBtn.textContent = "Pause";
            processQueue();
        } else {
            uploadSession.isPaused = true;
            pauseBtn.textContent = "Resume";
        }
    });

});
