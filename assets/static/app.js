document.addEventListener("DOMContentLoaded", () => {

    // ------------------------
    // GLOBAL STATE
    // ------------------------
    let currentState = { path: "", parentPath: "", itemToDelete: null };
    let currentData = [];
    let currentVersion = 0;

    const $ = (id) => document.getElementById(id);

    // ------------------------
    // DOM ELEMENTS
    // ------------------------
    const fileList = $("file-list");

    const fileUploadInput = $("file-upload");
    const fileUploadFilename = $("file-upload-filename");
    const fileRenameInput = $("file-rename-input");

    const startUploadBtn = $("start-upload-btn");
    const pauseUploadBtn = $("pause-upload-btn");
    const cancelUploadBtn = $("cancel-upload-btn");

    const step1 = $("upload-step-1");
    const step2 = $("upload-step-2");

    const progressBar = $("upload-progress-bar");
    const progressText = $("upload-percentage");
    const statusText = $("upload-status-text");
    const uploadModal = $("upload-file-modal");
    const uploadProgressContainer = $("upload-progress-container"); // optional

    const deleteConfirmModal = $("delete-confirm-modal");
    const deleteConfirmForm = $("delete-confirm-form");
    const deleteItemNameSpan = $("delete-item-name");
    const deletePasswordInput = $("delete-password");

    const createFolderModal = $("create-folder-modal");
    const createFolderForm = $("create-folder-form");
    const newFolderNameInput = $("new-folder-name");

    const settingsModal = $("settings-modal");

    const pathText = $("current-path-text");
    const backButton = $("back-button");
    const searchContainer = $("search-container");
    const searchInput = $("search-input");
    const searchBtn = $("search-button");
    const closeSearchBtn = $("close-search");

    const fabMain = $("fab-main");
    const fabMenu = $("fab-menu");
    const newFolderBtn = $("new-folder-btn");
    const newFileBtn = $("new-file-btn");
    const navSettings = $("nav-settings");

    const modalOverlay = $("modal-overlay");
    const loadingSpinner = $("loading-spinner");
    const toast = $("toast-notification");
    const toastMessage = $("toast-message");

    const closeButtons = document.querySelectorAll("[data-close-modal]");

    const userRole = (window.userRole || "").toLowerCase();
    const isAdmin = userRole === "admin";

    // ------------------------
    // ROLE-BASED UI LOCK
    // ------------------------
    // Viewer: no FAB, no upload, no create folder, no delete
    if (!isAdmin) {
        if (fabMain) fabMain.style.display = "none";
        if (fabMenu) fabMenu.style.display = "none";
        if (newFolderBtn) newFolderBtn.style.display = "none";
        if (newFileBtn) newFileBtn.style.display = "none";
    }

    // ------------------------
    // ICONS
    // ------------------------
    const icons = {
    // -----------------------------
    // FOLDERS & GENERIC FILE
    // -----------------------------
    folder: `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#58A6FF">
            <path d="M10 4H4C2.9 4 2 4.9 2 6V18C2 19.1 2.9 20 4 20H20C21.1 20 22 19.1 22 18V8C22 6.9 21.1 6 20 6H12L10 4Z"/>
        </svg>
    `,

    file: `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#8B949E">
            <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2Z" />
            <path d="M14 2V8H20" fill="#8B949E" />
        </svg>
    `,

    // -----------------------------
    // MEDIA
    // -----------------------------
    image: `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#A371F7">
            <path d="M21 19V5C21 3.9 20.1 3 19 3H5C3.9 3 3 3.9 3 5V19C3 20.1 3.9 21 5 21H19C20.1 21 21 20.1 21 19ZM8.5 11.5L11 14.5L14.5 10L19 16H5L8.5 11.5Z"/>
        </svg>
    `,

    video: `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#F178B6">
            <path d="M17 10.5V7C17 5.9 16.1 5 15 5H5C3.9 5 3 5.9 3 7V17C3 18.1 3.9 19 5 19H15C16.1 19 17 18.1 17 17V13.5L21 17V7L17 10.5Z"/>
        </svg>
    `,

    audio: `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#FACC15">
            <path d="M12 3V14.55A3.95 3.95 0 0 0 10 14C7.8 14 6 15.8 6 18S7.8 22 10 22 14 20.2 14 18V8H18V3H12Z"/>
        </svg>
    `,

    // -----------------------------
    // DOCUMENTS (PDF, DOCX, XLSX, PPTX)
    // -----------------------------
    pdf: `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#E11D48">
            <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2Z"/>
            <text x="7" y="17" fill="white" font-size="7" font-family="Arial" font-weight="bold">PDF</text>
        </svg>
    `,

    word: `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#3B82F6">
            <path d="M14 2H6V22H18V8L14 2Z"/>
            <text x="7" y="17" fill="white" font-size="7" font-family="Arial" font-weight="bold">DOC</text>
        </svg>
    `,

    excel: `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#22C55E">
            <path d="M14 2H6V22H18V8L14 2Z"/>
            <text x="7" y="17" fill="white" font-size="7" font-family="Arial" font-weight="bold">XLS</text>
        </svg>
    `,

    ppt: `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#EA580C">
            <path d="M14 2H6V22H18V8L14 2Z"/>
            <text x="7" y="17" fill="white" font-size="7" font-family="Arial" font-weight="bold">PPT</text>
        </svg>
    `,

    // -----------------------------
    // ARCHIVES (zip / rar)
    // -----------------------------
    zip: `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#FBBF24">
            <path d="M14 2H6V22H18V8L14 2Z"/>
            <text x="7" y="17" fill="black" font-size="7" font-family="Arial" font-weight="bold">ZIP</text>
        </svg>
    `,

    // -----------------------------
    // CODE FILES
    // -----------------------------
    code: `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#38BDF8">
            <path d="M14 2H6V22H18V8L14 2Z"/>
            <text x="7" y="17" fill="white" font-size="7" font-family="Arial" font-weight="bold">&lt;/&gt;</text>
        </svg>
    `,

    // -----------------------------
    // ACTION ICONS
    // -----------------------------
    download: `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#238636">
            <path d="M12 16L7 11H10V4H14V11H17L12 16Z"/>
            <path d="M5 18H19V20H5V18Z"/>
        </svg>
    `,

    delete: `
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#DA3633">
            <path d="M6 19C6 20.1 6.9 21 8 21H16C17.1 21 18 20.1 18 19V7H6V19Z"/>
            <path d="M15.5 4L14.5 3H9.5L8.5 4H5V6H19V4H15.5Z"/>
        </svg>
    `
};

    // ------------------------
    // UI HELPERS
    // ------------------------
    const showSpinner = () => loadingSpinner?.classList.add("active");
    const hideSpinner = () => loadingSpinner?.classList.remove("active");

    const showToast = (msg) => {
        if (!toast) {
            alert(msg);
            return;
        }
        toastMessage.textContent = msg;
        toast.classList.add("active");
        setTimeout(() => toast.classList.remove("active"), 2500);
    };

    const openModal = (m) => {
        if (!m) return;
        m.classList.add("active");
        if (modalOverlay) modalOverlay.classList.add("active");
    };

    const closeModal = (m) => {
        if (!m) return;
        m.classList.remove("active");
        if (modalOverlay) modalOverlay.classList.remove("active");
    };

    const closeAllModals = () => {
        [uploadModal, createFolderModal, deleteConfirmModal, settingsModal].forEach(m => m && m.classList.remove("active"));
        if (modalOverlay) modalOverlay.classList.remove("active");
        if (deletePasswordInput) deletePasswordInput.value = "";
    };

    // ------------------------
    // RENDER FILES
    // ------------------------
    const renderFiles = (items) => {
        if (!fileList) return;

        if (!items || items.length === 0) {
            fileList.innerHTML = `<p class="empty-folder">No items found</p>`;
            return;
        }

        fileList.innerHTML = items.map(item => {
            const showDelete = isAdmin;
            return `
                <div class="file-item" data-path="${item.path}" data-is-dir="${item.is_dir}" data-name="${item.name}">
                    <div class="item-icon ${item.file_type}">${icons[item.file_type] || icons.file} </div>
                    <div class="item-details">
                        <span class="item-name">${item.name}</span>
                        <span class="item-size">${item.size}</span>
                    </div>
                    <div class="item-actions">
                        <button class="icon-button download" data-path="${item.path}">${icons.download}</button>
                        ${showDelete ? `<button class="icon-button delete" data-path="${item.path}" data-name="${item.name}">${icons.delete}</button>` : ""}
                    </div>
                </div>
            `;
        }).join("");
    };

    // ------------------------
    // FETCH FILES
    // ------------------------
    async function fetchFiles(path) {
        if (path == null) path = ""; // defensive
        showSpinner();
        try {
            const res = await fetch(`/api/browse/${path}`);
            if (res.status === 401) {
                window.location.href = "/login";
                return;
            }
            if (!res.ok) {
                console.error("Browse error", res.status);
                return;
            }

            const data = await res.json();

            currentState.path = data.path || "";
            currentData = data.items || [];

            if (pathText) {
                pathText.textContent = data.path ? `/${data.path}` : "/";
            }

            if (backButton) {
                backButton.style.display = (data.breadcrumbs && data.breadcrumbs.length > 0) ? "block" : "none";
            }

            if (data.breadcrumbs && data.breadcrumbs.length > 1) {
                currentState.parentPath = data.breadcrumbs[data.breadcrumbs.length - 2].path || "";
            } else {
                currentState.parentPath = "";
            }

            renderFiles(currentData);

        } catch (e) {
            console.error(e);
        } finally {
            hideSpinner();
        }
    }

    // ------------------------
    // UPLOAD ENGINE (ADMIN ONLY)
    // ------------------------
    const generateId = () => Math.random().toString(36).slice(2);

    let uploadSession = {
        file: null,
        customName: null,
        chunkSize: 50 * 1024 * 1024,
        totalChunks: 0,
        chunksCompleted: 0,
        isPaused: false,
        isMerging: false,
        fileId: null,
        path: "",
        activeConnections: 0,
        maxConcurrency: 4,
        nextChunkToIndex: 0
    };

    const resetUploadSession = () => {
        uploadSession = {
            file: null,
            customName: null,
            chunkSize: 50 * 1024 * 1024,
            totalChunks: 0,
            chunksCompleted: 0,
            isPaused: false,
            isMerging: false,
            fileId: null,
            path: "",
            activeConnections: 0,
            maxConcurrency: 4,
            nextChunkToIndex: 0
        };
    };

    const resetUploadUI = () => {
        resetUploadSession();

        if (step1) step1.style.display = "block";
        if (step2) step2.style.display = "none";
        if (uploadProgressContainer) uploadProgressContainer.style.display = "none";

        if (fileUploadInput) fileUploadInput.value = "";
        if (fileUploadFilename) fileUploadFilename.textContent = "Click to Select File";

        if (fileRenameInput) {
            fileRenameInput.value = "";
            fileRenameInput.style.display = "none";
        }

        if (startUploadBtn) {
            startUploadBtn.textContent = "Start Upload";
            startUploadBtn.style.display = "inline-block";
        }

        if (pauseUploadBtn) {
            pauseUploadBtn.style.display = "none";
            pauseUploadBtn.textContent = "Pause";
            pauseUploadBtn.disabled = false;
        }

        if (progressBar) {
            progressBar.style.width = "0%";
        }

        if (progressText) {
            progressText.textContent = "0%";
        }

        if (statusText) {
            statusText.textContent = "Uploading...";
            statusText.style.color = "#8B949E";
        }
    };

    const performChunkUpload = async (index) => {
        uploadSession.activeConnections++;

        const start = index * uploadSession.chunkSize;
        const end = Math.min(start + uploadSession.chunkSize, uploadSession.file.size);
        const chunk = uploadSession.file.slice(start, end);

        const fd = new FormData();
        fd.append("file", chunk);
        fd.append("chunkIndex", index);
        fd.append("totalChunks", uploadSession.totalChunks);
        fd.append("fileId", uploadSession.fileId);
        fd.append("filename", uploadSession.customName);
        fd.append("path", uploadSession.path);
        fd.append("totalSize", uploadSession.file.size);

        try {
            const res = await fetch("/api/upload_chunk", {
                method: "POST",
                body: fd
            });

            const data = await res.json();

            if (!data.success) {
                throw new Error(data.error || "Upload failed");
            }

            // Last chunk triggers merge
            if (data.merging) {
                uploadSession.isMerging = true;

                if (progressBar) progressBar.style.width = "100%";
                if (progressText) progressText.textContent = "100%";
                if (statusText) {
                    statusText.textContent = "Merging...";
                    statusText.style.color = "#238636";
                }
                if (pauseUploadBtn) pauseUploadBtn.disabled = true;

                // Give server a moment to merge, watchdog will bump version
                setTimeout(() => {
                    showToast("Upload complete");
                    fetchFiles(currentState.path);
                    resetUploadUI();
                    if (uploadModal) closeModal(uploadModal);
                }, 1500);

                return;
            }

            // Regular chunk completed
            uploadSession.chunksCompleted++;

            // Guard: never let percent > 100
            let percent = 0;
            if (uploadSession.totalChunks > 0) {
                percent = Math.round(
                    (uploadSession.chunksCompleted / uploadSession.totalChunks) * 100
                );
                if (percent > 100) percent = 100;
            }

            if (progressBar) progressBar.style.width = percent + "%";
            if (progressText) progressText.textContent = percent + "%";

            processQueue();

        } catch (err) {
            console.error(err);

            if (!uploadSession.isPaused && !uploadSession.isMerging) {
                uploadSession.isPaused = true;
                if (statusText) {
                    statusText.textContent = "Network error. Paused.";
                    statusText.style.color = "#DA3633";
                }
                if (pauseUploadBtn) {
                    pauseUploadBtn.textContent = "Resume";
                    pauseUploadBtn.style.display = "inline-block";
                }
                if (startUploadBtn) startUploadBtn.style.display = "none";
            }
        } finally {
            uploadSession.activeConnections = Math.max(0, uploadSession.activeConnections - 1);
        }
    };

    const processQueue = () => {
        if (uploadSession.isPaused || uploadSession.isMerging) return;

        while (
            uploadSession.activeConnections < uploadSession.maxConcurrency &&
            uploadSession.nextChunkToIndex < uploadSession.totalChunks
        ) {
            const idx = uploadSession.nextChunkToIndex;
            uploadSession.nextChunkToIndex++;
            performChunkUpload(idx);
        }
    };

    // ------------------------
    // UPLOAD EVENT LISTENERS (ADMIN ONLY)
    // ------------------------
    if (isAdmin && fileUploadInput) {
        fileUploadInput.addEventListener("change", () => {
            const file = fileUploadInput.files[0];
            if (!file) {
                if (fileUploadFilename) fileUploadFilename.textContent = "No file chosen";
                if (fileRenameInput) fileRenameInput.style.display = "none";
                return;
            }
            if (fileUploadFilename) fileUploadFilename.textContent = file.name;
            if (fileRenameInput) {
                fileRenameInput.style.display = "block";
                fileRenameInput.value = file.name;
            }
        });
    }

    if (isAdmin && startUploadBtn) {
        startUploadBtn.addEventListener("click", (e) => {
            e.preventDefault();

            if (!fileUploadInput || !fileUploadInput.files.length) {
                showToast("Select a file first");
                return;
            }

            const file = fileUploadInput.files[0];

            // Optional max size limit (if provided by template)
            if (window.maxUploadBytes && Number(window.maxUploadBytes) > 0) {
                const limit = Number(window.maxUploadBytes);
                if (file.size > limit) {
                    showToast(
                        `File too large. Max is ${Math.round(limit / 1024 / 1024)} MB`
                    );
                    return;
                }
            }

            resetUploadSession();

            uploadSession.file = file;
            uploadSession.customName =
                (fileRenameInput && fileRenameInput.value.trim()) || file.name;

            uploadSession.totalChunks = Math.ceil(
                file.size / uploadSession.chunkSize
            );
            uploadSession.isPaused = false;
            uploadSession.isMerging = false;
            uploadSession.fileId = generateId();
            uploadSession.path = currentState.path;
            uploadSession.nextChunkToIndex = 0;

            if (step1) step1.style.display = "none";
            if (step2) step2.style.display = "block";
            if (uploadProgressContainer) uploadProgressContainer.style.display = "block";

            if (pauseUploadBtn) {
                pauseUploadBtn.style.display = "inline-block";
                pauseUploadBtn.textContent = "Pause";
            }

            if (progressBar) progressBar.style.width = "0%";
            if (progressText) progressText.textContent = "0%";
            if (statusText) {
                statusText.textContent = "Uploading...";
                statusText.style.color = "#8B949E";
            }

            processQueue();
        });
    }

    if (isAdmin && pauseUploadBtn) {
        pauseUploadBtn.addEventListener("click", () => {
            uploadSession.isPaused = !uploadSession.isPaused;
            pauseUploadBtn.textContent = uploadSession.isPaused ? "Resume" : "Pause";
            if (!uploadSession.isPaused) processQueue();
        });
    }

    if (isAdmin && cancelUploadBtn) {
        cancelUploadBtn.addEventListener("click", () => {
            uploadSession.isPaused = true;
            resetUploadUI();
            if (uploadModal) closeModal(uploadModal);
        });
    }

    // ------------------------
    // DELETE ITEM (ADMIN ONLY)
    // ------------------------
    if (isAdmin && deleteConfirmForm) {
        deleteConfirmForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            if (!currentState.itemToDelete) return;

            const pwd = deletePasswordInput.value;
            if (!pwd) {
                showToast("Password required");
                return;
            }

            showSpinner();
            try {
                const res = await fetch("/api/delete", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        path: currentState.itemToDelete.path,
                        password: pwd
                    })
                });
                const data = await res.json();

                if (res.ok && data.success) {
                    showToast("Deleted");
                    closeModal(deleteConfirmModal);
                    deletePasswordInput.value = "";
                    fetchFiles(currentState.path);
                } else {
                    showToast(data.error || "Delete failed");
                }
            } catch (err) {
                console.error(err);
                showToast("Error deleting item");
            } finally {
                hideSpinner();
            }
        });
    }

    // ------------------------
    // CREATE FOLDER (ADMIN ONLY)
    // ------------------------
    if (isAdmin && createFolderForm) {
        createFolderForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const name = newFolderNameInput.value.trim();
            if (!name) {
                showToast("Folder name required");
                return;
            }

            showSpinner();
            try {
                const res = await fetch("/api/create_folder", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        folder_name: name,
                        path: currentState.path
                    })
                });

                if (res.ok) {
                    showToast("Folder created");
                    closeModal(createFolderModal);
                    newFolderNameInput.value = "";
                    fetchFiles(currentState.path);
                } else {
                    showToast("Failed to create folder");
                }
            } catch (err) {
                console.error(err);
                showToast("Error creating folder");
            } finally {
                hideSpinner();
            }
        });
    }

    // ------------------------
    // SEARCH
    // ------------------------
    if (searchInput) {
        searchInput.addEventListener("keyup", () => {
            const q = searchInput.value.toLowerCase();
            if (!q) {
                renderFiles(currentData);
                return;
            }
            renderFiles(
                currentData.filter(i => i.name.toLowerCase().includes(q))
            );
        });
    }

    if (searchBtn) {
        searchBtn.addEventListener("click", () => {
            if (!searchContainer) return;
            searchContainer.style.display = "flex";
            searchInput && searchInput.focus();
        });
    }

    if (closeSearchBtn) {
        closeSearchBtn.addEventListener("click", () => {
            if (!searchContainer) return;
            searchContainer.style.display = "none";
            if (searchInput) searchInput.value = "";
            renderFiles(currentData);
        });
    }

    // ------------------------
    // FILE CLICK HANDLER
    // ------------------------
    if (fileList) {
        fileList.addEventListener("click", (e) => {
            const t = e.target.closest("button, .file-item");
            if (!t) return;

            const path = t.dataset.path;

            if (t.classList.contains("delete")) {
                if (!isAdmin) {
                    showToast("You do not have permission to delete");
                    return;
                }
                currentState.itemToDelete = { path, name: t.dataset.name };
                if (deleteItemNameSpan) deleteItemNameSpan.textContent = t.dataset.name;
                openModal(deleteConfirmModal);
                return;
            }

            if (t.classList.contains("download")) {
                window.location.href = `/api/download/${path}`;
                return;
            }

            if (t.classList.contains("file-item")) {
                if (t.dataset.isDir === "true") {
                    fetchFiles(path);
                } else {
                    window.open(`/api/view/${path}`, "_blank");
                }
            }
        });
    }

    // ------------------------
    // UI Buttons
    // ------------------------
    if (newFolderBtn && isAdmin) {
        newFolderBtn.addEventListener("click", () => openModal(createFolderModal));
    }

    if (newFileBtn && isAdmin) {
        newFileBtn.addEventListener("click", () => openModal(uploadModal));
    }

    if (navSettings) {
        navSettings.addEventListener("click", () => openModal(settingsModal));
    }

    if (backButton) {
        backButton.addEventListener("click", () => {
            fetchFiles(currentState.parentPath || "");
        });
    }

    if (fabMain && fabMenu && isAdmin) {
        fabMain.addEventListener("click", () => {
            fabMain.classList.toggle("active");
            fabMenu.classList.toggle("active");
        });
    }

    closeButtons.forEach(b => {
        b.addEventListener("click", closeAllModals);
    });

    if (modalOverlay) {
        modalOverlay.addEventListener("click", closeAllModals);
    }

    // ------------------------
    // LONG-POLLING
    // ------------------------
    async function pollUpdates() {
        try {
            const res = await fetch(`/api/check_updates?version=${currentVersion}`);
            if (res.status === 401) {
                // session expired
                window.location.href = "/login";
                return;
            }
            if (!res.ok) {
                console.error("check_updates error", res.status);
            } else {
                const data = await res.json();
                if (data.update) {
                    currentVersion = data.version;
                    fetchFiles(currentState.path);
                }
            }
        } catch (e) {
            console.error("Polling error", e);
        } finally {
            setTimeout(pollUpdates, 1500);
        }
    }

    pollUpdates();

    // initial load
    fetchFiles("");

});
