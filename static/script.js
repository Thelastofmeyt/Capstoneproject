/**
 * script.js - Core UI and Logic for Shakespeare WebApp
 * Integrated with OCR Upload, Manual Search, and Library Management.
 */

// --- Theme toggle with persistence ---
function toggleTheme() {
    const isLight = document.body.classList.toggle('light');
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
    console.log(`DEBUG: Theme toggled to ${isLight ? 'light' : 'dark'}.`);
}

function loadTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
        document.body.classList.add('light');
    }
}

// --- Navigation page loader ---
function loadPage(page) {
    if (page === 'dashboard') {
        window.location.href = '/';
    } else {
        window.location.href = `/${page}`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Theme immediately
    loadTheme();

    // 2. Global UI Selectors
    const resultsContainer = document.getElementById('book-cards-grid');
    const loadingMessage = document.getElementById('loadingMessage');
    
    // Support both naming conventions for the search input
    const manualSearchInput = document.getElementById('ocrTextSearch') || document.getElementById('manualSearchInput');
    const manualSearchBtn = document.getElementById('manualSearchBtn');
    
    const confirmModal = document.getElementById('confirmModal');
    const modalMessage = document.getElementById('modalMessage');
    const modalConfirmBtn = document.getElementById('modalConfirmBtn');
    const modalCancelBtn = document.getElementById('modalCancelBtn');

    // --- Custom Modal Helper ---
    function showModal(message, onConfirm = null, isConfirm = false) {
        if (!confirmModal) return;
        modalMessage.textContent = message;
        confirmModal.classList.remove('hidden');
        
        if (isConfirm) modalCancelBtn.classList.remove('hidden');
        else modalCancelBtn.classList.add('hidden');

        const handleConfirm = () => {
            confirmModal.classList.add('hidden');
            if (onConfirm) onConfirm();
            cleanup();
        };

        const handleCancel = () => {
            confirmModal.classList.add('hidden');
            cleanup();
        };

        function cleanup() {
            modalConfirmBtn.removeEventListener('click', handleConfirm);
            modalCancelBtn.removeEventListener('click', handleCancel);
        }

        modalConfirmBtn.addEventListener('click', handleConfirm);
        modalCancelBtn.addEventListener('click', handleCancel);
    }

    // --- 3. OCR Upload Page Logic (Fixes Upload Click Issue) ---
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const imagePreview = document.getElementById('image-preview');
    const uploadForm = document.getElementById('uploadForm');

    if (dropzone && fileInput) {
        // Makes the entire box clickable to open file dialog
        dropzone.addEventListener('click', () => fileInput.click());

        fileInput.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    imagePreview.src = e.target.result;
                    imagePreview.classList.remove('hidden');
                    // Hide the "Drag and Drop" text
                    const instructions = dropzone.querySelector('p');
                    if (instructions) instructions.classList.add('hidden');
                }
                reader.readAsDataURL(file);
            }
        });

        // Simple Drag & Drop Visuals
        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('border-blue-500');
        });

        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('border-blue-500');
        });

        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                fileInput.dispatchEvent(new Event('change'));
            }
        });
    }

    // Show loading state on form submit
    if (uploadForm) {
        uploadForm.addEventListener('submit', () => {
            const btn = uploadForm.querySelector('button[type="submit"]');
            if (btn) {
                btn.disabled = true;
                btn.textContent = "Processing OCR...";
            }
        });
    }

    // --- 4. OCR & Search Results Rendering ---
    function renderBookCards(books) {
        if (!resultsContainer) return;
        resultsContainer.innerHTML = '';
        
        if (loadingMessage) loadingMessage.classList.add('hidden');
        
        if (!books || books.length === 0) {
            resultsContainer.innerHTML = '<p class="text-center text-gray-500 col-span-full py-10">No books found. Try a manual search above.</p>';
            return;
        }

        books.forEach(book => {
            const card = document.createElement('div');
            card.className = "bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden border border-gray-200 dark:border-gray-700 flex flex-col p-4 transition-transform hover:scale-105";
            
            const safeBook = JSON.stringify(book).replace(/'/g, "&apos;");

            card.innerHTML = `
                <div class="relative h-48 mb-4 overflow-hidden rounded bg-gray-100 dark:bg-gray-900 flex items-center justify-center">
                    <img src="${book.thumbnail || 'https://via.placeholder.com/150x200?text=No+Cover'}" 
                         alt="${book.title}" class="h-full object-contain">
                </div>
                <h3 class="font-bold text-lg text-gray-900 dark:text-white truncate" title="${book.title}">${book.title}</h3>
                <p class="text-sm text-gray-600 dark:text-gray-400 mb-2 truncate">By ${book.author}</p>
                <p class="text-xs text-gray-500 line-clamp-3 mb-4 flex-grow">${book.description || 'No description available.'}</p>
                <div class="mt-auto pt-2">
                    <button class="add-to-library-btn w-full bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded-lg transition-colors"
                            data-book='${safeBook}'>
                        Add to Library
                    </button>
                </div>
            `;
            resultsContainer.appendChild(card);
        });
    }

    // Manual Search logic
    if (manualSearchBtn && manualSearchInput) {
        const performSearch = async () => {
            const query = manualSearchInput.value.trim();
            if (!query) return;

            manualSearchBtn.disabled = true;
            manualSearchBtn.innerHTML = '<span class="animate-pulse">Searching...</span>';
            if (loadingMessage) loadingMessage.classList.remove('hidden');

            try {
                // Querying the Google Books API
                const response = await fetch(`https://www.googleapis.com/books/v1/volumes?q=${encodeURIComponent(query)}&maxResults=10`);
                const data = await response.json();
                
                const formattedBooks = (data.items || []).map(item => {
                    const info = item.volumeInfo;
                    return {
                        title: info.title || 'Unknown Title',
                        author: (info.authors || ['Unknown Author']).join(', '),
                        description: info.description || 'No description available.',
                        thumbnail: info.imageLinks?.thumbnail || '',
                        isbn: info.industryIdentifiers?.[0]?.identifier || 'N/A'
                    };
                });
                renderBookCards(formattedBooks);
            } catch (err) {
                console.error("DEBUG: Search error:", err);
                showModal("Search failed. Please check your connection.");
            } finally {
                manualSearchBtn.disabled = false;
                manualSearchBtn.textContent = 'Manual Search';
            }
        };

        manualSearchBtn.addEventListener('click', performSearch);
        manualSearchInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') performSearch(); });

        // --- AUTO-TRIGGER SEARCH FIX ---
        // If the input has text (from OCR), start the search immediately
        if (manualSearchInput.value.trim() !== "") {
            console.log("DEBUG: Auto-triggering search for OCR text.");
            performSearch();
        }
    }

    // --- 5. Library Actions (Delegated) ---
    document.addEventListener('click', async (event) => {
        if (event.target.classList.contains('add-to-library-btn')) {
            const button = event.target;
            const bookData = JSON.parse(button.dataset.book);
            const originalContent = button.innerHTML;

            button.disabled = true;
            button.innerHTML = 'Adding...';

            try {
                // Ensure this matches your route in app.py (usually /add_to_library)
                const response = await fetch('/api/add_book', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(bookData)
                });
                const result = await response.json();
                if (result.success) {
                    button.className = "w-full bg-gray-400 text-white font-bold py-2 px-4 rounded-lg cursor-not-allowed";
                    button.textContent = 'Added!';
                    showModal(`Successfully added "${bookData.title}".`);
                } else { throw new Error(result.message); }
            } catch (error) {
                button.disabled = false;
                button.innerHTML = originalContent;
                showModal('Error: ' + error.message);
            }
        }

        if (event.target.classList.contains('delete-button')) {
            const bookId = event.target.dataset.bookId;
            showModal('Remove this book from library?', () => {
                const form = document.createElement('form');
                form.action = `/delete_book/${bookId}`;
                form.method = 'post';
                document.body.appendChild(form);
                form.submit();
            }, true);
        }
    });

    // --- 6. Dashboard Charts ---
    const ctx = document.getElementById('myChart');
    if (ctx) {
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Books Added',
                    data: [1, 4, 2, 7, 5, 3, 2],
                    borderColor: '#66BB6A',
                    backgroundColor: 'rgba(102, 187, 106, 0.2)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: { responsive: true, maintainAspectRatio: false }
        });
    }

    // --- 7. Socket.IO & Flash Handling ---
    if (typeof io !== 'undefined') {
        const socket = io();
        socket.on('notification', (data) => {
            const list = document.getElementById('notification-list');
            if (list) {
                const li = document.createElement('li');
                li.className = "p-3 border-b border-gray-100 dark:border-gray-700 text-green-600";
                li.textContent = data.message || "Update received.";
                list.prepend(li);
            }
        });
    }

    window.toggleSidebar = function() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            const isCollapsed = sidebar.classList.toggle('collapsed');
            localStorage.setItem('sidebarCollapsed', isCollapsed);
        }
    };
    
    if (localStorage.getItem('sidebarCollapsed') === 'true') {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) sidebar.classList.add('collapsed');
    }

    document.querySelectorAll('.flash').forEach(flash => {
        setTimeout(() => {
            flash.style.opacity = '0';
            setTimeout(() => flash.remove(), 500);
        }, 4000);
    });
});
