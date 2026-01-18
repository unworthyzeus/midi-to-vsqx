/**
 * MIDI to VSQX Converter - Frontend Script V2
 * Handles file uploads, form submission, UI interactions
 * NEW: Channel-to-lyrics mapping, improved preview, smart matching options
 */

document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const form = document.getElementById('converter-form');
    const midiInput = document.getElementById('midi-file');
    const lyricsInput = document.getElementById('lyrics-file');
    const midiZone = document.getElementById('midi-zone');
    const lyricsZone = document.getElementById('lyrics-zone');
    const midiFilename = document.getElementById('midi-filename');
    const lyricsFilename = document.getElementById('lyrics-filename');
    const manualLyricsContainer = document.getElementById('manual-lyrics-container');
    const previewBtn = document.getElementById('preview-btn');
    const convertBtn = document.getElementById('convert-btn');
    const previewPanel = document.getElementById('preview-panel');
    const previewStats = document.getElementById('preview-stats');
    const previewContent = document.getElementById('preview-content');
    const closePreview = document.getElementById('close-preview');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');
    const toastContainer = document.getElementById('toast-container');

    // State
    let channelLyricsMapping = {};  // { channelId: lyricsText }
    let analyzedChannels = [];      // Stored channel info after MIDI analysis
    let currentPreviewData = null;  // Last preview data
    let lastAnalyzedFile = null;    // Cache for last analyzed file to avoid lag
    let selectedChannelId = null;   // Explicitly selected channel for preview/convert

    // File upload handling
    setupFileUpload(midiInput, midiZone, midiFilename);
    setupFileUpload(lyricsInput, lyricsZone, lyricsFilename);

    // Auto-analyze MIDI when uploaded
    midiInput.addEventListener('change', async () => {
        if (midiInput.files.length > 0) {
            const file = midiInput.files[0];
            if (lastAnalyzedFile === file.name + file.size) return;
            lastAnalyzedFile = file.name + file.size;
            await analyzeMidi();
        }
    });

    // Lyrics source radio handling
    document.querySelectorAll('input[name="lyrics_source"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            if (e.target.value === 'manual') {
                manualLyricsContainer.classList.add('visible');
            } else {
                manualLyricsContainer.classList.remove('visible');
            }

            if (e.target.value === 'file') {
                lyricsZone.classList.add('required-hint');
            } else {
                lyricsZone.classList.remove('required-hint');
            }
        });
    });

    // Preview button
    previewBtn.addEventListener('click', async () => {
        if (!validateForm()) return;

        showLoading('Generating preview...');

        try {
            const formData = new FormData(form);

            // Add channel-specific lyrics mapping
            formData.append('channel_lyrics_mapping', JSON.stringify(channelLyricsMapping));

            // Add smart matching options
            const wordBoundaries = document.getElementById('respect-word-boundaries')?.checked ?? true;
            const autoSyllabify = document.getElementById('auto-syllabify')?.checked ?? true;
            const phraseGap = document.getElementById('phrase-gap')?.value ?? 400;
            const multiTrack = document.getElementById('vsqx-multi-track')?.checked ?? false;
            const overlapMs = document.getElementById('overlap-ms')?.value ?? 10;
            const splitLogic = document.querySelector('input[name="split_logic"]:checked')?.value ?? 'melody';

            formData.append('respect_word_boundaries', wordBoundaries ? 'true' : 'false');
            formData.append('auto_syllabify', autoSyllabify ? 'true' : 'false');
            formData.append('phrase_gap_threshold', phraseGap);
            formData.append('multi_track', multiTrack ? 'true' : 'false');
            formData.append('overlap_ms', overlapMs);
            formData.append('split_logic', splitLogic);
            if (selectedChannelId !== null) {
                formData.append('selected_channel', selectedChannelId);
            }

            const response = await fetch('/api/preview', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Preview failed');
            }

            const data = await response.json();
            currentPreviewData = data;
            displayPreview(data);

        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            hideLoading();
        }
    });

    // Convert button (form submit)
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!validateForm()) return;

        showLoading('Converting...');

        try {
            const formData = new FormData(form);

            // Add channel-specific lyrics mapping
            formData.append('channel_lyrics_mapping', JSON.stringify(channelLyricsMapping));

            // Add smart matching options
            const wordBoundaries = document.getElementById('respect-word-boundaries')?.checked ?? true;
            const autoSyllabify = document.getElementById('auto-syllabify')?.checked ?? true;
            const phraseGap = document.getElementById('phrase-gap')?.value ?? 400;
            const multiTrack = document.getElementById('vsqx-multi-track')?.checked ?? false;
            const overlapMs = document.getElementById('overlap-ms')?.value ?? 10;
            const splitLogic = document.querySelector('input[name="split_logic"]:checked')?.value ?? 'melody';

            formData.append('respect_word_boundaries', wordBoundaries ? 'true' : 'false');
            formData.append('auto_syllabify', autoSyllabify ? 'true' : 'false');
            formData.append('phrase_gap_threshold', phraseGap);
            formData.append('multi_track', multiTrack ? 'true' : 'false');
            formData.append('overlap_ms', overlapMs);
            formData.append('split_logic', splitLogic);
            if (selectedChannelId !== null) {
                formData.append('selected_channel', selectedChannelId);
            }

            const response = await fetch('/api/convert', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Conversion failed');
            }

            // Download the file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;

            // Get filename from Content-Disposition header or use default
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'output.vsqx';
            if (contentDisposition) {
                const match = contentDisposition.match(/filename="?(.+?)"?$/);
                if (match) filename = match[1];
            }

            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            showToast('File downloaded successfully!', 'success');

        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            hideLoading();
        }
    });

    // Close preview
    closePreview.addEventListener('click', () => {
        previewPanel.classList.remove('visible');
    });

    /**
     * Analyze MIDI file and show channel selection
     */
    async function analyzeMidi() {
        if (!midiInput.files.length) return;

        try {
            const formData = new FormData();
            formData.append('midi', midiInput.files[0]);

            // Pass advanced tuning to analysis too so split logic matches preview
            const overlapMs = document.getElementById('overlap-ms')?.value ?? 10;
            const splitLogic = document.querySelector('input[name="split_logic"]:checked')?.value ?? 'melody';
            formData.append('overlap_ms', overlapMs);
            formData.append('split_logic', splitLogic);

            const response = await fetch('/api/analyze', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) return;

            const data = await response.json();
            analyzedChannels = data.channels;

            // Auto-select recommended channel
            const recommended = data.channels.find(ch => ch.is_recommended);
            if (recommended) {
                selectedChannelId = recommended.channel_id;
            }

            // Show channel selector if multiple channels
            if (data.channels.length > 1) {
                showChannelSelector(data);
            }

        } catch (error) {
            console.error('MIDI analysis failed:', error);
        }
    }

    /**
     * Show channel selector UI
     */
    function showChannelSelector(data) {
        // Check if channel selector already exists
        let channelSection = document.getElementById('channel-section');
        if (!channelSection) {
            // Create channel section after lyrics section
            const lyricsSection = manualLyricsContainer.closest('.form-section');
            channelSection = document.createElement('div');
            channelSection.id = 'channel-section';
            channelSection.className = 'form-section channel-section';
            lyricsSection.insertAdjacentElement('afterend', channelSection);
        }

        channelSection.innerHTML = `
            <h2 class="section-title">
                <span class="section-number">✦</span>
                MIDI Channels (${data.channels.length} tracks detected)
            </h2>
            <div class="channel-grid-container">
                <div class="channel-grid" id="channel-grid">
                    ${data.channels.slice(0, 6).map(ch => renderChannelCard(ch, channelLyricsMapping)).join('')}
                    ${data.channels.length > 6 ? `
                        <div class="show-more-channels" id="show-more-channels-btn">
                            <span class="btn-text">+ ${data.channels.length - 6} more tracks hidden</span>
                            <button type="button" class="btn-text-action">Show All Tracks</button>
                        </div>
                        <div class="extra-channels hidden" id="extra-channels-grid">
                            ${data.channels.slice(6).map(ch => renderChannelCard(ch, channelLyricsMapping)).join('')}
                        </div>
                    ` : ''}
                </div>
            </div>
            <input type="file" id="channel-file-picker" style="display: none;" accept=".txt,.lrc,.srt">
        `;

        // Add toggle logic
        const showMoreBtn = document.getElementById('show-more-channels-btn');
        if (showMoreBtn) {
            showMoreBtn.addEventListener('click', () => {
                const extraGrid = document.getElementById('extra-channels-grid');
                extraGrid.classList.toggle('hidden');
                showMoreBtn.querySelector('button').textContent = extraGrid.classList.contains('hidden') ? 'Show All Tracks' : 'Show Less';
                if (!extraGrid.classList.contains('hidden')) {
                    showMoreBtn.querySelector('.btn-text').style.display = 'none';
                } else {
                    showMoreBtn.querySelector('.btn-text').style.display = 'inline';
                }
            });
        }

        function renderChannelCard(ch, mapping) {
            const isSelected = selectedChannelId !== null && String(ch.channel_id) === String(selectedChannelId);
            return `
                <div class="channel-card ${ch.is_recommended ? 'recommended' : ''} ${isSelected ? 'selected' : ''}" data-channel-id="${ch.channel_id}">
                    <div class="channel-header">
                        <span class="channel-name">${ch.name}</span>
                        ${ch.is_recommended ? '<span class="channel-badge">Recommended</span>' : ''}
                    </div>
                    <div class="channel-info">
                        <span class="channel-stat">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                                <path d="M9 18V5l12-2v13"/>
                            </svg>
                            ${ch.note_count} notes
                        </span>
                        <span class="channel-stat">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                            </svg>
                            ${ch.pitch_range.min_name} - ${ch.pitch_range.max_name}
                        </span>
                        ${ch.is_polyphonic ? '<span class="channel-tag poly">Voice Split</span>' : ''}
                    </div>
                    <div class="channel-lyrics-input">
                        <div class="channel-lyrics-header">
                            <label for="channel-lyrics-${ch.channel_id}">Channel Lyrics</label>
                            <button type="button" class="btn-text-action load-file-btn" data-channel-id="${ch.channel_id}">
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12">
                                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14,2 14,8 20,8"/>
                                </svg>
                                Load File
                            </button>
                        </div>
                        <textarea 
                            id="channel-lyrics-${ch.channel_id}" 
                            placeholder="Enter lyrics for this channel..."
                            rows="3"
                        >${mapping[ch.channel_id] || ''}</textarea>
                    </div>
                </div>
            `;
        }

        // Listen for "Load File" buttons
        const filePicker = document.getElementById('channel-file-picker');
        let activeChannelId = null;

        channelSection.querySelectorAll('.channel-card').forEach(card => {
            card.addEventListener('click', (e) => {
                // Don't trigger if clicking textarea or button
                if (e.target.tagName === 'TEXTAREA' || e.target.closest('.load-file-btn')) return;

                const chId = card.dataset.channelId;
                selectedChannelId = chId;

                // Update UI
                channelSection.querySelectorAll('.channel-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');

                // Update preview if panel is open
                if (previewPanel.classList.contains('visible')) {
                    previewBtn.click();
                }
            });
        });

        channelSection.querySelectorAll('.load-file-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                activeChannelId = btn.dataset.channelId;
                filePicker.click();
            });
        });

        filePicker.addEventListener('change', (e) => {
            if (e.target.files.length > 0 && activeChannelId !== null) {
                const file = e.target.files[0];
                const reader = new FileReader();
                reader.onload = (event) => {
                    const content = event.target.result;
                    const textarea = document.getElementById(`channel-lyrics-${activeChannelId}`);
                    if (textarea) {
                        textarea.value = content;
                        channelLyricsMapping[activeChannelId] = content;
                        textarea.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                };
                reader.readAsText(file);
                filePicker.value = ''; // Reset for next use
            }
        });

        // Listen for lyrics input changes
        channelSection.querySelectorAll('textarea').forEach(textarea => {
            textarea.addEventListener('input', (e) => {
                const channelId = e.target.id.replace('channel-lyrics-', '');
                const value = e.target.value.trim();
                if (value) {
                    channelLyricsMapping[channelId] = value;
                } else {
                    delete channelLyricsMapping[channelId];
                }
            });
        });
    }

    /**
     * Setup file upload zone with drag & drop
     */
    function setupFileUpload(input, zone, filenameEl) {
        input.addEventListener('change', () => {
            if (input.files.length > 0) {
                filenameEl.textContent = input.files[0].name;
                zone.classList.add('has-file');
            } else {
                filenameEl.textContent = '';
                zone.classList.remove('has-file');
            }
        });

        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('dragover');
        });

        zone.addEventListener('dragleave', () => {
            zone.classList.remove('dragover');
        });

        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('dragover');

            if (e.dataTransfer.files.length > 0) {
                input.files = e.dataTransfer.files;
                input.dispatchEvent(new Event('change'));
            }
        });
    }

    /**
     * Validate form before submission
     */
    function validateForm() {
        if (!midiInput.files.length) {
            showToast('Please select a MIDI file', 'error');
            midiZone.classList.add('error');
            setTimeout(() => midiZone.classList.remove('error'), 2000);
            return false;
        }

        const lyricsSource = document.querySelector('input[name="lyrics_source"]:checked').value;
        if (lyricsSource === 'file' && !lyricsInput.files.length) {
            showToast('Please select a lyrics file or choose a different lyrics source', 'error');
            return false;
        }

        return true;
    }

    /**
     * Display preview data with enhanced info
     */
    function displayPreview(data) {
        // Stats section with channels
        let channelHTML = '';
        if (data.channels && data.channels.length > 0) {
            channelHTML = `
                <div class="stat-section">
                    <span class="stat-section-title">Channels</span>
                    <div class="channel-pills">
                        ${data.channels.map(ch => `
                            <span class="channel-pill ${ch.channel_id === data.selected_channel ? 'selected' : ''} ${ch.has_custom_lyrics ? 'custom' : ''}" data-channel-id="${ch.channel_id}">
                                ${ch.name} 
                                <span class="similarity">${ch.similarity}%</span>
                            </span>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        previewStats.innerHTML = `
            <div class="stats-grid">
                <div class="stat-item">
                    <span class="stat-label">Tempo</span>
                    <span class="stat-value">${data.tempo.toFixed(1)} BPM</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Time Sig</span>
                    <span class="stat-value">${data.time_signature[0]}/${data.time_signature[1]}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Notes</span>
                    <span class="stat-value">${data.total_notes}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Lyrics</span>
                    <span class="stat-value">${data.total_lyrics}</span>
                </div>
                <div class="stat-item highlight">
                    <span class="stat-label">Match Score</span>
                    <span class="stat-value ${data.similarity_score > 80 ? 'good' : data.similarity_score > 50 ? 'ok' : 'low'}">${data.similarity_score}%</span>
                </div>
            </div>
            ${channelHTML}
        `;

        // Enhanced table with word boundary indicators
        let tableHTML = `
            <table class="preview-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Note</th>
                        <th>Start</th>
                        <th>Duration</th>
                        <th>Lyric</th>
                    </tr>
                </thead>
                <tbody>
        `;

        data.matched_notes.forEach((note, i) => {
            const classes = [];
            if (note.was_split) classes.push('note-split');
            if (note.is_word_start && !note.is_word_end) classes.push('word-start');
            if (!note.is_word_start && note.is_word_end) classes.push('word-end');
            if (!note.is_word_start && !note.is_word_end) classes.push('word-mid');

            const classStr = classes.join(' ');
            const lyricDisplay = note.lyric === '-' ? '<span class="lyric-continue">—</span>' : escapeHtml(note.lyric);

            tableHTML += `
                <tr class="${classStr}">
                    <td>${i + 1}</td>
                    <td><span class="note-name">${note.pitch_name}</span> <span class="note-midi">(${note.pitch})</span></td>
                    <td>${note.start.toFixed(0)} ms</td>
                    <td>${note.duration.toFixed(0)} ms</td>
                    <td class="lyric-cell">${lyricDisplay}</td>
                </tr>
            `;
        });

        if (data.has_more) {
            tableHTML += `
                <tr class="more-row">
                    <td colspan="5">
                        <span class="more-indicator">... and ${data.total_notes - 100} more notes</span>
                    </td>
                </tr>
            `;
        }

        tableHTML += '</tbody></table>';
        previewContent.innerHTML = tableHTML;

        previewPanel.classList.add('visible');
        previewPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });

        // Add listeners to pills
        previewStats.querySelectorAll('.channel-pill').forEach(pill => {
            pill.addEventListener('click', () => {
                const chId = pill.dataset.channelId;
                selectedChannelId = chId;

                // Update selection in the main channel grid too
                const channelSection = document.getElementById('channel-section');
                if (channelSection) {
                    channelSection.querySelectorAll('.channel-card').forEach(card => {
                        card.classList.toggle('selected', String(card.dataset.channelId) === String(chId));
                    });
                }

                // Re-trigger preview with new channel
                previewBtn.click();
            });
        });
    }

    /**
     * Show loading overlay
     */
    function showLoading(text = 'Loading...') {
        loadingText.textContent = text;
        loadingOverlay.classList.add('visible');
    }

    /**
     * Hide loading overlay
     */
    function hideLoading() {
        loadingOverlay.classList.remove('visible');
    }

    /**
     * Show toast notification
     */
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease reverse forwards';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    /**
     * Escape HTML entities
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', (e) => {
            e.preventDefault();
            const target = document.querySelector(anchor.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
});
