document.addEventListener('DOMContentLoaded', () => {
    // --- STATE ---
    let currentState = { path: '', parentPath: '', itemToDelete: null };
    let currentData = []; 

    // --- DOM ELEMENTS ---
    const $ = (id) => document.getElementById(id);
    
    // Core Views
    const fileList = $('file-list');
    
    // Upload Elements
    const fileUploadInput = $('file-upload');
    const fileUploadFilename = $('file-upload-filename');
    const fileRenameInput = $('file-rename-input');
    const startUploadBtn = $('start-upload-btn');
    const pauseUploadBtn = $('pause-upload-btn');
    const cancelUploadBtn = $('cancel-upload-btn');
    const step1 = $('upload-step-1');
    const step2 = $('upload-step-2');
    const progressBar = $('upload-progress-bar');
    const progressText = $('upload-percentage');
    const statusText = $('upload-status-text');
    const uploadModal = $('upload-file-modal'); 
    const uploadProgressContainer = $('upload-progress-container'); 

    // Admin Only Elements
    const deleteConfirmModal = $('delete-confirm-modal');
    const deleteConfirmForm = $('delete-confirm-form');
    const deleteItemNameSpan = $('delete-item-name');
    const deletePasswordInput = $('delete-password');
    const createFolderModal = $('create-folder-modal');
    const createFolderForm = $('create-folder-form');
    const newFolderNameInput = $('new-folder-name');
    const settingsModal = $('settings-modal'); // <--- DEFINED HERE
    
    const pathText = $('current-path-text');
    const backButton = $('back-button');
    const searchContainer = $('search-container');
    const searchInput = $('search-input');
    const searchBtn = $('search-button');
    const closeSearchBtn = $('close-search');
    const fabMain = $('fab-main');
    const fabMenu = $('fab-menu');
    const newFolderBtn = $('new-folder-btn');
    const newFileBtn = $('new-file-btn');
    const navSettings = $('nav-settings'); // Settings Button

    // Common Elements
    const modalOverlay = $('modal-overlay');
    const loadingSpinner = $('loading-spinner');
    const toast = $('toast-notification');
    const toastMessage = $('toast-message');
    const closeButtons = document.querySelectorAll('[data-close-modal]');

    // --- PARALLEL UPLOAD STATE ---
    let uploadSession = {
        file: null,
        customName: null,
        chunkSize: 10 * 1024 * 1024, 
        totalChunks: 0,
        chunksCompleted: 0,
        isPaused: false,
        isMerging: false,
        fileId: null,
        path: '',
        activeConnections: 0,
        maxConcurrency: 4,
        nextChunkToIndex: 0
    };

    const icons = {
        folder: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#58A6FF"><path d="M10 4H4c-1.103 0-2 .897-2 2v14c0 1.103.897 2 2 2h16c1.103 0 2-.897 2-2V8c0-1.103-.897-2-2-2h-8l-2-2z"/></svg>',
        file: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#8B949E"><path d="M6 22h12a2 2 0 0 0 2-2V8l-6-6H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2zm7-18 5 5h-5V4z"/></svg>',
        image: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#A371F7"><path d="M19 3H5c-1.103 0-2 .897-2 2v14c0 1.103.897 2 2 2h14c1.103 0 2-.897 2-2V5c0-1.103-.897-2-2-2zM5 19V5h14v14H5zm4-6 3 4 5-6 2 3V7H7v6z"/></svg>',
        video: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#F178B6"><path d="M18 7a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V7zM8 7h8v10H8V7z"/><path d="m10 16 5-3.5-5-3.5v7z"/></svg>',
        download: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#238636"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>',
        delete: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#DA3633"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>'
    };

    // --- UI HELPERS ---
    const showSpinner = () => { if(loadingSpinner) loadingSpinner.classList.add('active'); };
    const hideSpinner = () => { if(loadingSpinner) loadingSpinner.classList.remove('active'); };
    const showToast = (msg) => {
        if(!toast) { alert(msg); return; }
        toastMessage.textContent = msg;
        toast.classList.add('active');
        setTimeout(() => toast.classList.remove('active'), 3000);
    };
    
    const openModal = (m) => { 
        if(m && modalOverlay) { 
            m.classList.add('active'); 
            modalOverlay.classList.add('active'); 
            if(fabMain) fabMain.classList.remove('active'); 
            if(fabMenu) fabMenu.classList.remove('active'); 
        }
    };
    const closeModal = (m) => { if(m && modalOverlay) { m.classList.remove('active'); modalOverlay.classList.remove('active'); }};
    
    const closeAllModals = () => {
        // FIX: Added settingsModal to the list so it closes properly
        [createFolderModal, uploadModal, deleteConfirmModal, settingsModal].forEach(m => {
            if (m) closeModal(m);
        });
        
        if(deletePasswordInput) deletePasswordInput.value = "";
        if(uploadSession.file && !uploadSession.isPaused && uploadSession.chunksCompleted < uploadSession.totalChunks) { /* warn? */ }
    };

    const renderFiles = (items) => {
        if(!fileList) return;
        if (items.length === 0) { fileList.innerHTML = `<p class="empty-folder">No items found</p>`; return; }
        fileList.innerHTML = items.map(item => {
            const showDelete = window.userRole === 'admin';
            return `
            <div class="file-item" data-path="${item.path}" data-is-dir="${item.is_dir}" data-name="${item.name}">
                <div class="item-icon ${item.file_type}">${icons[item.file_type] || icons.file}</div>
                <div class="item-details"><span class="item-name">${item.name}</span><span class="item-size">${item.size}</span></div>
                <div class="item-actions">
                    <button class="icon-button download" data-path="${item.path}">${icons.download}</button>
                    ${showDelete ? `<button class="icon-button delete" data-path="${item.path}" data-name="${item.name}">${icons.delete}</button>` : ''}
                </div>
            </div>`;
        }).join('');
    };

    const fetchFiles = async (path) => {
        if(!fileList) return; 
        showSpinner();
        try {
            const res = await fetch(`/api/browse/${path}`);
            if(res.status === 401) window.location.href = '/login';
            const data = await res.json();
            currentState.path = data.path;
            currentData = data.items;
            pathText.textContent = data.path === "" ? "/" : "/" + data.path;
            backButton.style.display = data.breadcrumbs.length > 0 ? 'block' : 'none';
            if (data.breadcrumbs.length > 0) currentState.parentPath = data.breadcrumbs.length > 1 ? data.breadcrumbs[data.breadcrumbs.length - 2].path : '';
            renderFiles(currentData);
        } catch (e) { console.error(e); } finally { hideSpinner(); }
    };

    // --- UPLOAD ENGINE ---
    const generateId = () => Math.random().toString(36).substr(2, 9);

    const resetUploadUI = () => {
        if(step1) step1.style.display = 'block';
        if(step2) step2.style.display = 'none';
        if(uploadProgressContainer) uploadProgressContainer.style.display = 'none'; 
        
        if(fileUploadInput) fileUploadInput.value = '';
        if(fileUploadFilename) fileUploadFilename.textContent = "Click to Select File";
        if(fileRenameInput) { fileRenameInput.value = ""; fileRenameInput.style.display = "none"; }

        if(startUploadBtn) { startUploadBtn.style.display = "inline-block"; startUploadBtn.textContent = "Start Upload"; }
        if(pauseUploadBtn) { pauseUploadBtn.textContent = "Pause"; pauseUploadBtn.style.display = "none"; }

        uploadSession = { file: null, customName: null, chunkSize: 50 * 1024 * 1024, totalChunks: 0, chunksCompleted: 0, isPaused: false, isMerging: false, fileId: null, path: '', activeConnections: 0, maxConcurrency: 6, nextChunkToIndex: 0 };
        
        if(progressBar) { progressBar.style.width = '0%'; progressBar.className = ''; }
        if(progressText) progressText.textContent = '0%';
        if(statusText) { statusText.textContent = 'Uploading...'; statusText.style.color = '#8B949E'; }
        
        if(pauseUploadBtn) pauseUploadBtn.disabled = false;
    };

    const performChunkUpload = async (index) => {
        uploadSession.activeConnections++;
        const start = index * uploadSession.chunkSize;
        const end = Math.min(start + uploadSession.chunkSize, uploadSession.file.size);
        const chunk = uploadSession.file.slice(start, end);

        const fd = new FormData();
        fd.append('file', chunk);
        fd.append('chunkIndex', index);
        fd.append('totalChunks', uploadSession.totalChunks);
        fd.append('fileId', uploadSession.fileId);
        fd.append('filename', uploadSession.customName || uploadSession.file.name);
        fd.append('path', uploadSession.path);
        fd.append('totalSize', uploadSession.file.size);
        if(window.mySocketId) fd.append('socketId', window.mySocketId);

        try {
            const res = await fetch('/api/upload_chunk', { method: 'POST', body: fd });
            const data = await res.json();

            if (data.success) {
                uploadSession.activeConnections--;
                if (data.completed) {
                    showToast('Upload Complete!');
                    if(uploadModal && uploadModal.classList.contains('modal')) closeModal(uploadModal);
                    resetUploadUI();
                    if(fileList) fetchFiles(currentState.path);
                } else {
                    // Merging check
                    if (data.merging) {
                        uploadSession.isMerging = true;
                        progressBar.classList.add('progress-bar-merging');
                        progressBar.style.width = '100%';
                        progressText.textContent = '100%';
                        statusText.textContent = 'Merging file (Do not close)...';
                        statusText.style.color = '#238636';
                        if(pauseUploadBtn) pauseUploadBtn.disabled = true;
                        return; // Stop queue, wait for socket
                    }

                    uploadSession.chunksCompleted++;
                    const percent = Math.round((uploadSession.chunksCompleted / uploadSession.totalChunks) * 100);
                    if (!uploadSession.isMerging) {
                        progressBar.style.width = percent + '%';
                        progressText.textContent = percent + '%';
                    }
                    processQueue();
                }
            } else { throw new Error(data.error); }
        } catch (e) {
            console.error(e);
            uploadSession.activeConnections--;
            if (uploadSession.isMerging) return;

            if (!uploadSession.isPaused) {
                uploadSession.isPaused = true;
                statusText.textContent = "Network Error. Paused.";
                statusText.style.color = "#DA3633";
                if(pauseUploadBtn) {
                    pauseUploadBtn.textContent = "Resume";
                    pauseUploadBtn.style.display = "inline-block";
                }
                if(startUploadBtn) startUploadBtn.style.display = "none";
                uploadSession.nextChunkToIndex = index; 
            }
        }
    };

    const processQueue = () => {
        if (uploadSession.isPaused || uploadSession.isMerging || uploadSession.chunksCompleted === uploadSession.totalChunks) return;
        while (uploadSession.activeConnections < uploadSession.maxConcurrency && uploadSession.nextChunkToIndex < uploadSession.totalChunks) {
            performChunkUpload(uploadSession.nextChunkToIndex);
            uploadSession.nextChunkToIndex++;
        }
    };

    // --- EVENT LISTENERS ---
    if(fileUploadInput) {
        fileUploadInput.addEventListener('change', () => {
            const file = fileUploadInput.files[0];
            if(file) {
                fileUploadFilename.textContent = file.name;
                if(fileRenameInput) { fileRenameInput.style.display = "block"; fileRenameInput.value = file.name; }
            } else {
                fileUploadFilename.textContent = "No file chosen";
                if(fileRenameInput) fileRenameInput.style.display = "none";
            }
        });
    }

    if(startUploadBtn) {
        startUploadBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (!fileUploadInput.files.length) { showToast("Select a file first"); return; }
            const file = fileUploadInput.files[0];
            if (window.maxUploadBytes && window.maxUploadBytes > 0) {
                if (file.size > window.maxUploadBytes) {
                    showToast(`File too large! Limit is ${Math.round(window.maxUploadBytes/1024/1024)}MB`);
                    return;
                }
            }
            uploadSession.file = file;
            if(fileRenameInput && fileRenameInput.value.trim() !== "") {
                uploadSession.customName = fileRenameInput.value.trim();
            } else {
                uploadSession.customName = file.name;
            }
            uploadSession.totalChunks = Math.ceil(file.size / uploadSession.chunkSize);
            uploadSession.currentChunk = 0;
            uploadSession.isPaused = false;
            uploadSession.isMerging = false; 
            uploadSession.fileId = generateId();
            uploadSession.path = (fileList) ? currentState.path : '';

            if(step1 && step2) {
                step1.style.display = 'none';
                step2.style.display = 'block';
                pauseUploadBtn.style.display = "inline-block";
            } else if(uploadProgressContainer) {
                uploadProgressContainer.style.display = 'block';
                startUploadBtn.style.display = 'none';
                pauseUploadBtn.style.display = 'inline-block';
            }
            processQueue();
        });
    }

    if(pauseUploadBtn) {
        pauseUploadBtn.addEventListener('click', () => {
            if (uploadSession.isPaused) {
                uploadSession.isPaused = false;
                pauseUploadBtn.textContent = "Pause";
                statusText.textContent = "Uploading...";
                statusText.style.color = "#8B949E";
                processQueue();
            } else {
                uploadSession.isPaused = true;
                pauseUploadBtn.textContent = "Resume";
                statusText.textContent = "Paused";
            }
        });
    }

    if(cancelUploadBtn) {
        cancelUploadBtn.addEventListener('click', () => {
            uploadSession.isPaused = true;
            resetUploadUI();
            if(uploadModal && uploadModal.classList.contains('modal')) closeModal(uploadModal);
        });
    }

    if(deleteConfirmForm) {
        deleteConfirmForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if(!currentState.itemToDelete) return;
            const pwd = deletePasswordInput.value;
            if (!pwd) { showToast("Password required"); return; }
            showSpinner();
            try {
                const res = await fetch('/api/delete', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ path: currentState.itemToDelete.path, password: pwd }) });
                const data = await res.json();
                if(res.ok && data.success) { showToast('Deleted'); closeModal(deleteConfirmModal); deletePasswordInput.value = ""; fetchFiles(currentState.path); }
                else { showToast(data.error || "Delete failed"); }
            } catch(e) { showToast("Error"); } finally { hideSpinner(); }
        });
    }

    if(createFolderForm) {
        createFolderForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            showSpinner();
            const res = await fetch('/api/create_folder', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ folder_name: newFolderNameInput.value, path: currentState.path }) });
            hideSpinner();
            if(res.ok) { showToast('Folder created'); closeModal(createFolderModal); newFolderNameInput.value=''; fetchFiles(currentState.path); }
        });
    }

    if(searchInput) {
        searchInput.addEventListener('keyup', () => {
            const query = searchInput.value.toLowerCase();
            if (!query) { renderFiles(currentData); return; }
            renderFiles(currentData.filter(item => item.name.toLowerCase().includes(query)));
        });
    }
    if(searchBtn) searchBtn.addEventListener('click', () => { searchContainer.style.display = 'flex'; searchInput.focus(); });
    if(closeSearchBtn) closeSearchBtn.addEventListener('click', () => { searchContainer.style.display = 'none'; searchInput.value = ''; renderFiles(currentData); });

    if(fileList) {
        fileList.addEventListener('click', (e) => {
            const target = e.target.closest('button, .file-item');
            if(!target) return;
            const path = target.dataset.path;
            if(target.classList.contains('delete')) {
                 e.stopPropagation();
                 currentState.itemToDelete = { path, name: target.dataset.name };
                 deleteItemNameSpan.textContent = target.dataset.name;
                 openModal(deleteConfirmModal);
            } else if(target.classList.contains('download')) {
                 e.stopPropagation();
                 window.location.href = `/api/download/${path}`;
            } else if(target.classList.contains('file-item')) {
                 if(target.dataset.isDir === 'true') fetchFiles(path);
                 else window.open(`/api/view/${path}`, '_blank');
            }
        });
    }

    // --- FIXED: Listeners for Settings ---
    if(navSettings) {
        navSettings.addEventListener('click', () => openModal(settingsModal));
    }

    if(closeButtons) closeButtons.forEach(b => b.addEventListener('click', closeAllModals));
    if(modalOverlay) modalOverlay.addEventListener('click', closeAllModals);
    if(fabMain) fabMain.addEventListener('click', () => { fabMain.classList.toggle('active'); fabMenu.classList.toggle('active'); });
    if(newFolderBtn) newFolderBtn.addEventListener('click', () => openModal(createFolderModal));
    if(newFileBtn) newFileBtn.addEventListener('click', () => openModal(uploadModal));
    if(backButton) backButton.addEventListener('click', () => fetchFiles(currentState.parentPath));

    // --- SOCKET IO ---
    const socket = io({ transports: ['websocket', 'polling'], reconnection: true });
    
    window.mySocketId = null;
    socket.on('connect', () => {
        window.mySocketId = socket.id;
        console.log("ID:", window.mySocketId);
    });

    socket.on('reload_data', (msg) => {
        if (fileList && (currentState.path === msg.path || (msg.path === "" && currentState.path === ""))) {
            fetchFiles(currentState.path);
        }
    });

    socket.on('upload_status', (msg) => {
        if (msg.status === 'completed') {
            showToast('Upload Complete!');
            if(uploadModal && uploadModal.classList.contains('modal')) closeModal(uploadModal);
            resetUploadUI();
            if(fileList) fetchFiles(currentState.path);
        } else if (msg.status === 'error') {
            showToast('Merge Failed: ' + msg.error);
            statusText.textContent = "Server Error: " + msg.error;
            statusText.style.color = "#DA3633";
        }
    });

    // Hide Admin elements for Viewers
    if (window.userRole !== 'admin') {
        if (fabMain) fabMain.style.display = 'none';
        if (fabMenu) fabMenu.style.display = 'none';
        if (newFolderBtn) newFolderBtn.style.display = 'none';
        if (newFileBtn) newFileBtn.style.display = 'none';
        // if (navSettings) navSettings.style.display = 'none';
    }

    if(fileList) fetchFiles('');
});