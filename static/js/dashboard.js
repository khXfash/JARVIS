/**
 * JARVIS Front-Desk Receptionist - Meetings & Schedule Telemetry Dashboard
 * Strictly monitoring and read-only telemetry for autonomous AI agent operations.
 */

(function () {
    "use strict";

    // State management
    const state = {
        activeFilter: "all",
        searchQuery: "",
        dateFilter: "",
        viewMode: "cards", // 'cards' | 'table'
        autoRefresh: true,
        refreshIntervalMs: 10000,
        refreshTimer: null,
        stats: null,
        meetings: [],
    };

    // DOM Elements Cache
    const DOM = {
        liveClock: document.getElementById("liveClockDisplay"),
        headerTodayDate: document.getElementById("headerTodayDate"),
        lastUpdatedTimestamp: document.getElementById("lastUpdatedTimestamp"),
        autoRefreshBtn: document.getElementById("autoRefreshBtn"),
        autoRefreshLabel: document.getElementById("autoRefreshLabel"),
        syncSpinIcon: document.getElementById("syncSpinIcon"),
        manualRefreshBtn: document.getElementById("manualRefreshBtn"),
        syncGoogleBtn: document.getElementById("syncGoogleBtn"),
        
        // KPI Stat Elements
        statTotalMeetings: document.getElementById("statTotalMeetings"),
        statTodayMeetings: document.getElementById("statTodayMeetings"),
        statUpcomingMeetings: document.getElementById("statUpcomingMeetings"),
        statSyncedMeetings: document.getElementById("statSyncedMeetings"),
        statSyncStatusBadge: document.getElementById("statSyncStatusBadge"),
        
        // Tab Badges
        tabBadgeAll: document.getElementById("tabBadgeAll"),
        tabBadgeToday: document.getElementById("tabBadgeToday"),
        tabBadgeUpcoming: document.getElementById("tabBadgeUpcoming"),
        tabBadgePast: document.getElementById("tabBadgePast"),
        tabBadgeCancelled: document.getElementById("tabBadgeCancelled"),
        filterTabsNav: document.getElementById("filterTabsNav"),
        
        // Search & Filters
        searchInput: document.getElementById("searchInput"),
        clearSearchBtn: document.getElementById("clearSearchBtn"),
        dateFilterInput: document.getElementById("dateFilterInput"),
        clearDateBtn: document.getElementById("clearDateBtn"),
        viewCardsBtn: document.getElementById("viewCardsBtn"),
        viewTableBtn: document.getElementById("viewTableBtn"),
        
        // Spotlight Section
        spotlightSection: document.getElementById("spotlightSection"),
        spotlightBadgeText: document.getElementById("spotlightBadgeText"),
        spotlightTitle: document.getElementById("spotlightTitle"),
        spotlightTimeRange: document.getElementById("spotlightTimeRange"),
        spotlightDuration: document.getElementById("spotlightDuration"),
        spotlightDate: document.getElementById("spotlightDate"),
        spotlightPhone: document.getElementById("spotlightPhone"),
        spotlightClientPhoneWrap: document.getElementById("spotlightClientPhoneWrap"),
        spotlightCountdownVal: document.getElementById("spotlightCountdownVal"),
        spotlightCountdownLabel: document.getElementById("spotlightCountdownLabel"),
        spotlightGoogleLink: document.getElementById("spotlightGoogleLink"),
        
        // Timeline Strip
        timelineHoursBar: document.getElementById("timelineHoursBar"),
        timelineSlotSummary: document.getElementById("timelineSlotSummary"),
        
        // Containers
        resultsStrip: document.getElementById("resultsStrip"),
        resultsCountText: document.getElementById("resultsCountText"),
        activeFilterBadge: document.getElementById("activeFilterBadge"),
        meetingsGridView: document.getElementById("meetingsGridView"),
        meetingsTableView: document.getElementById("meetingsTableView"),
        meetingsTableBody: document.getElementById("meetingsTableBody"),
        emptyStateView: document.getElementById("emptyStateView"),
        emptySubtext: document.getElementById("emptySubtext"),
        
        // Activity Drawer
        openActivityBtn: document.getElementById("openActivityBtn"),
        activityDrawerOverlay: document.getElementById("activityDrawerOverlay"),
        closeDrawerBtn: document.getElementById("closeDrawerBtn"),
        drawerCallsTab: document.getElementById("drawerCallsTab"),
        drawerNotesTab: document.getElementById("drawerNotesTab"),
        drawerCallsList: document.getElementById("drawerCallsList"),
        drawerNotesList: document.getElementById("drawerNotesList"),
        drawerCallCount: document.getElementById("drawerCallCount"),
        drawerNoteCount: document.getElementById("drawerNoteCount"),
        topCallCountBadge: document.getElementById("topCallCountBadge"),
        
        // Toast
        toastContainer: document.getElementById("toastContainer"),
    };

    // =========================================================================
    // Initialization
    // =========================================================================
    function init() {
        startLiveClock();
        setupEventListeners();
        loadDashboardData();
        loadDrawerCalls();
        setupAutoRefresh();
    }

    // =========================================================================
    // Clock & Live Timers
    // =========================================================================
    function startLiveClock() {
        function updateClock() {
            const now = new Date();
            const timeOptions = { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: true };
            if (DOM.liveClock) {
                DOM.liveClock.textContent = now.toLocaleTimeString(undefined, timeOptions);
            }
            if (DOM.headerTodayDate) {
                const dateOptions = { weekday: "long", year: "numeric", month: "long", day: "numeric" };
                DOM.headerTodayDate.textContent = "Today is " + now.toLocaleDateString(undefined, dateOptions);
            }
        }
        updateClock();
        setInterval(updateClock, 1000);
    }

    // =========================================================================
    // Auto-Refresh
    // =========================================================================
    function setupAutoRefresh() {
        if (state.refreshTimer) {
            clearInterval(state.refreshTimer);
            state.refreshTimer = null;
        }
        if (state.autoRefresh) {
            state.refreshTimer = setInterval(() => {
                loadDashboardData(true);
            }, state.refreshIntervalMs);
        }
    }

    function toggleAutoRefresh() {
        state.autoRefresh = !state.autoRefresh;
        if (state.autoRefresh) {
            DOM.autoRefreshBtn.classList.add("active");
            DOM.autoRefreshLabel.textContent = "Auto-Refresh: ON";
            showToast("Live telemetry active (refreshing every 10s)", "info");
            setupAutoRefresh();
        } else {
            DOM.autoRefreshBtn.classList.remove("active");
            DOM.autoRefreshLabel.textContent = "Auto-Refresh: OFF";
            if (state.refreshTimer) {
                clearInterval(state.refreshTimer);
                state.refreshTimer = null;
            }
            showToast("Auto-refresh paused", "info");
        }
    }

    // =========================================================================
    // Data Loading & API Calls
    // =========================================================================
    async function loadDashboardData(isSilent = false) {
        if (!isSilent && DOM.syncSpinIcon) {
            DOM.syncSpinIcon.classList.add("spinning");
        }

        try {
            await Promise.all([fetchStats(), fetchMeetings()]);
            if (DOM.lastUpdatedTimestamp) {
                const now = new Date();
                DOM.lastUpdatedTimestamp.textContent = `Last telemetry update: ${now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`;
            }
        } catch (err) {
            console.error("Dashboard fetch error:", err);
            if (!isSilent) {
                showToast("Failed to fetch meetings: " + err.message, "error");
            }
        } finally {
            if (DOM.syncSpinIcon) {
                setTimeout(() => DOM.syncSpinIcon.classList.remove("spinning"), 400);
            }
        }
    }

    async function fetchStats() {
        const res = await fetch("/api/stats");
        if (!res.ok) throw new Error("Stats request failed");
        const json = await res.json();
        if (json.status === "success") {
            state.stats = json.data;
            renderStats(json.data);
            renderSpotlight(json.data);
            renderTimelineStrip(json.data);
        }
    }

    async function fetchMeetings() {
        const params = new URLSearchParams();
        if (state.activeFilter && state.activeFilter !== "all") {
            params.set("filter", state.activeFilter);
        }
        if (state.searchQuery) {
            params.set("search", state.searchQuery);
        }
        if (state.dateFilter) {
            params.set("date", state.dateFilter);
        }

        const res = await fetch(`/api/meetings?${params.toString()}`);
        if (!res.ok) throw new Error("Meetings list failed");
        const json = await res.json();
        if (json.status === "success") {
            state.meetings = json.data;
            renderMeetings(json.data);
        }
    }

    // =========================================================================
    // Rendering: KPI Stats & Spotlight
    // =========================================================================
    function renderStats(s) {
        if (!s) return;
        if (DOM.statTotalMeetings) DOM.statTotalMeetings.textContent = s.total_meetings;
        if (DOM.statTodayMeetings) DOM.statTodayMeetings.textContent = s.today_meetings;
        if (DOM.statUpcomingMeetings) DOM.statUpcomingMeetings.textContent = s.upcoming_meetings + (s.in_progress_meetings || 0);
        if (DOM.statSyncedMeetings) DOM.statSyncedMeetings.textContent = s.synced_meetings;

        if (DOM.statSyncStatusBadge) {
            const pct = s.total_meetings > 0 ? Math.round((s.synced_meetings / s.total_meetings) * 100) : 100;
            DOM.statSyncStatusBadge.textContent = `${pct}% Synced`;
        }

        // Update tab badges
        if (DOM.tabBadgeAll) DOM.tabBadgeAll.textContent = s.total_meetings;
        if (DOM.tabBadgeToday) DOM.tabBadgeToday.textContent = s.today_meetings;
        if (DOM.tabBadgeUpcoming) DOM.tabBadgeUpcoming.textContent = s.upcoming_meetings + (s.in_progress_meetings || 0);
        if (DOM.tabBadgePast) DOM.tabBadgePast.textContent = s.past_meetings;
        if (DOM.tabBadgeCancelled) DOM.tabBadgeCancelled.textContent = s.cancelled_meetings;
    }

    function renderSpotlight(s) {
        if (!s || (!s.active_meeting && !s.next_meeting)) {
            if (DOM.spotlightSection) DOM.spotlightSection.style.display = "none";
            return;
        }

        const meeting = s.active_meeting || s.next_meeting;
        if (DOM.spotlightSection) DOM.spotlightSection.style.display = "block";

        const isInProgress = meeting.is_in_progress;
        if (DOM.spotlightBadgeText) {
            DOM.spotlightBadgeText.textContent = isInProgress ? "NOW IN CONSULTATION" : "NEXT PATIENT UPCOMING";
        }
        if (DOM.spotlightTitle) {
            DOM.spotlightTitle.textContent = meeting.title || `Appointment: ${meeting.client_name}`;
        }
        if (DOM.spotlightTimeRange) {
            DOM.spotlightTimeRange.textContent = meeting.time_range || `${meeting.start_time_label} – ${meeting.end_time_label}`;
        }
        if (DOM.spotlightDuration) {
            DOM.spotlightDuration.textContent = `(${meeting.duration_str})`;
        }
        if (DOM.spotlightDate) {
            DOM.spotlightDate.textContent = meeting.formatted_date || meeting.short_date;
        }
        if (DOM.spotlightPhone && DOM.spotlightClientPhoneWrap) {
            if (meeting.client_phone) {
                DOM.spotlightPhone.textContent = meeting.client_phone;
                DOM.spotlightPhone.href = `tel:${meeting.client_phone}`;
                DOM.spotlightClientPhoneWrap.style.display = "flex";
            } else {
                DOM.spotlightClientPhoneWrap.style.display = "none";
            }
        }
        if (DOM.spotlightCountdownVal) {
            DOM.spotlightCountdownVal.textContent = meeting.relative_time || "Scheduled";
        }
        if (DOM.spotlightCountdownLabel) {
            DOM.spotlightCountdownLabel.textContent = isInProgress ? "Status" : "Starts in";
        }

        if (DOM.spotlightGoogleLink) {
            if (meeting.google_html_link) {
                DOM.spotlightGoogleLink.href = meeting.google_html_link;
                DOM.spotlightGoogleLink.style.display = "inline-flex";
            } else {
                DOM.spotlightGoogleLink.style.display = "none";
            }
        }
    }

    function renderTimelineStrip(s) {
        if (!DOM.timelineHoursBar) return;
        DOM.timelineHoursBar.innerHTML = "";

        const hours = [
            { label: "9 AM", hour: 9 },
            { label: "10 AM", hour: 10 },
            { label: "11 AM", hour: 11 },
            { label: "12 PM", hour: 12 },
            { label: "1 PM", hour: 13 },
            { label: "2 PM", hour: 14 },
            { label: "3 PM", hour: 15 },
            { label: "4 PM", hour: 16 },
            { label: "5 PM", hour: 17 },
            { label: "6 PM", hour: 18 },
        ];

        let activeCount = 0;
        hours.forEach(h => {
            const slotEl = document.createElement("div");
            slotEl.className = "timeline-hour-slot";
            
            let hasMeeting = false;
            let inProg = false;

            if (s && (s.active_meeting || s.today_meetings > 0)) {
                const m = s.active_meeting;
                if (m && m.is_today) {
                    try {
                        const startH = new Date(m.start_time).getHours();
                        const endH = new Date(m.end_time).getHours();
                        if (h.hour >= startH && h.hour < endH) {
                            hasMeeting = true;
                            inProg = m.is_in_progress;
                        }
                    } catch (e) {}
                }
            }

            if (hasMeeting) {
                slotEl.classList.add("has-meeting");
                activeCount++;
                if (inProg) slotEl.classList.add("in-progress");
            }

            slotEl.innerHTML = `
                <div class="slot-time">${h.label}</div>
                <div class="slot-status-bar"></div>
            `;
            DOM.timelineHoursBar.appendChild(slotEl);
        });

        if (DOM.timelineSlotSummary) {
            DOM.timelineSlotSummary.textContent = activeCount > 0 ? `${activeCount} slot(s) booked today` : "Open agenda today";
        }
    }

    // =========================================================================
    // Rendering: Meetings List & Grid (Pure Monitoring)
    // =========================================================================
    function renderMeetings(meetings) {
        if (DOM.resultsCountText) {
            DOM.resultsCountText.textContent = `Showing ${meetings.length} meeting${meetings.length === 1 ? '' : 's'}`;
        }
        if (DOM.activeFilterBadge) {
            let label = state.activeFilter.toUpperCase();
            if (state.dateFilter) label += ` • ${state.dateFilter}`;
            if (state.searchQuery) label += ` • "${state.searchQuery}"`;
            DOM.activeFilterBadge.textContent = label;
        }

        if (meetings.length === 0) {
            if (DOM.meetingsGridView) DOM.meetingsGridView.style.display = "none";
            if (DOM.meetingsTableView) DOM.meetingsTableView.style.display = "none";
            if (DOM.emptyStateView) {
                DOM.emptyStateView.style.display = "flex";
                if (state.searchQuery) {
                    DOM.emptySubtext.textContent = `No meetings matching "${state.searchQuery}".`;
                } else if (state.dateFilter) {
                    DOM.emptySubtext.textContent = `No meetings scheduled on ${state.dateFilter}.`;
                } else {
                    DOM.emptySubtext.textContent = `No meetings found in this view. Meetings are added autonomously by the AI voice agent during calls.`;
                }
            }
            return;
        }

        if (DOM.emptyStateView) DOM.emptyStateView.style.display = "none";

        if (state.viewMode === "cards") {
            if (DOM.meetingsGridView) DOM.meetingsGridView.style.display = "grid";
            if (DOM.meetingsTableView) DOM.meetingsTableView.style.display = "none";
            renderCardsView(meetings);
        } else {
            if (DOM.meetingsGridView) DOM.meetingsGridView.style.display = "none";
            if (DOM.meetingsTableView) DOM.meetingsTableView.style.display = "block";
            renderTableView(meetings);
        }
    }

    function renderCardsView(meetings) {
        if (!DOM.meetingsGridView) return;
        DOM.meetingsGridView.innerHTML = "";

        meetings.forEach(m => {
            const card = document.createElement("article");
            card.className = "meeting-card";
            if (m.is_today) card.classList.add("card-today");
            if (m.is_in_progress) card.classList.add("card-in-progress");
            if (m.status === "cancelled") card.classList.add("card-cancelled");

            const dayClass = m.is_today ? "today" : (m.is_tomorrow ? "tomorrow" : "past");
            const statusClass = m.timing_status;

            card.innerHTML = `
                <!-- Top Row: Day badge & Status -->
                <div class="card-top-row">
                    <span class="card-day-badge ${dayClass}">${escapeHtml(m.day_badge)}</span>
                    <span class="card-status-pill ${statusClass}">
                        ${m.is_in_progress ? '● In Progress' : (m.status === 'confirmed' ? '✓ Confirmed' : '✕ Cancelled')}
                    </span>
                </div>

                <!-- High Visibility Date & Time Box -->
                <div class="card-datetime-box">
                    <div class="card-date-label">
                        <svg class="meta-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
                            <line x1="16" y1="2" x2="16" y2="6"/>
                            <line x1="8" y1="2" x2="8" y2="6"/>
                            <line x1="3" y1="10" x2="21" y2="10"/>
                        </svg>
                        <span>${escapeHtml(m.formatted_date)}</span>
                    </div>
                    <div class="card-time-row">
                        <span class="card-time-range">${escapeHtml(m.time_range)}</span>
                        <span class="card-duration-chip">${escapeHtml(m.duration_str)}</span>
                    </div>
                    <div class="card-relative-time">${escapeHtml(m.relative_time)}</div>
                </div>

                <!-- Client Info & Meeting Title -->
                <div class="card-client-wrap">
                    <div class="client-avatar">${escapeHtml(m.client_initials)}</div>
                    <div class="client-info">
                        <h3 class="client-name" title="${escapeHtml(m.client_name)}">${escapeHtml(m.client_name)}</h3>
                        <p class="meeting-title" title="${escapeHtml(m.title)}">${escapeHtml(m.title)}</p>
                    </div>
                </div>

                <!-- Contacts Row -->
                <div class="card-contacts-row">
                    ${m.client_phone ? `
                        <a href="tel:${escapeHtml(m.client_phone)}" class="contact-chip" title="Call client">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
                            </svg>
                            <span>${escapeHtml(m.client_phone)}</span>
                        </a>
                    ` : ''}
                    ${m.client_email ? `
                        <a href="mailto:${escapeHtml(m.client_email)}" class="contact-chip" title="Email client">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="2" y="4" width="20" height="16" rx="2"/>
                                <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
                            </svg>
                            <span>${escapeHtml(m.client_email)}</span>
                        </a>
                    ` : ''}
                </div>

                <!-- Card Actions / Status Footer -->
                <div class="card-actions-footer">
                    ${m.google_html_link ? `
                        <a href="${escapeHtml(m.google_html_link)}" target="_blank" rel="noopener noreferrer" class="card-gcal-link" title="Open event in Google Calendar">
                            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                                <polyline points="15 3 21 3 21 9"/>
                                <line x1="10" y1="14" x2="21" y2="3"/>
                            </svg>
                            <span>Google Calendar</span>
                        </a>
                    ` : `
                        <span class="card-footnote" style="font-size:0.75rem; color:var(--text-muted)">Saved locally</span>
                    `}
                    <span class="agent-booked-badge" title="Booked autonomously by Nova AI Receptionist">
                        <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5">
                            <polyline points="20 6 9 17 4 12"/>
                        </svg>
                        <span>Nova AI Booked</span>
                    </span>
                </div>
            `;
            DOM.meetingsGridView.appendChild(card);
        });
    }

    function renderTableView(meetings) {
        if (!DOM.meetingsTableBody) return;
        DOM.meetingsTableBody.innerHTML = "";

        meetings.forEach(m => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>
                    <div class="table-date-val">${escapeHtml(m.short_date)}</div>
                    <div style="font-size:0.75rem; color:var(--text-muted)">${escapeHtml(m.day_of_week)}</div>
                </td>
                <td>
                    <div class="table-time-val">${escapeHtml(m.time_range)}</div>
                    <div style="font-size:0.75rem; color:var(--text-muted)">${escapeHtml(m.duration_str)} (${escapeHtml(m.relative_time)})</div>
                </td>
                <td>
                    <div class="table-client-cell">
                        <div class="client-avatar" style="width:32px; height:32px; font-size:0.75rem">${escapeHtml(m.client_initials)}</div>
                        <span style="font-weight:600; color:var(--text-heading)">${escapeHtml(m.client_name)}</span>
                    </div>
                </td>
                <td>
                    <div style="font-weight:500; color:var(--text-heading)">${escapeHtml(m.title)}</div>
                    ${m.description ? `<div style="font-size:0.75rem; color:var(--text-secondary)">${escapeHtml(m.description)}</div>` : ''}
                </td>
                <td>
                    <div style="display:flex; flex-direction:column; gap:0.2rem">
                        ${m.client_phone ? `<span style="font-family:var(--font-mono); font-size:0.8rem; color:var(--teal-700)">${escapeHtml(m.client_phone)}</span>` : '<span style="color:var(--text-muted)">—</span>'}
                        ${m.client_email ? `<span style="font-size:0.75rem; color:var(--text-secondary)">${escapeHtml(m.client_email)}</span>` : ''}
                    </div>
                </td>
                <td>
                    ${m.google_html_link ? `
                        <a href="${escapeHtml(m.google_html_link)}" target="_blank" rel="noopener noreferrer" class="card-gcal-link" style="font-size:0.78rem">
                            Synced ✓
                        </a>
                    ` : `<span style="color:var(--text-muted); font-size:0.78rem">Local</span>`}
                </td>
                <td>
                    <span class="card-status-pill ${m.timing_status}" style="font-size:0.68rem">
                        ${m.is_in_progress ? 'In Consultation' : (m.status === 'confirmed' ? 'Confirmed' : 'Cancelled')}
                    </span>
                </td>
                <td class="text-right">
                    <span class="agent-booked-badge" style="font-size:0.72rem" title="Autonomous Nova AI Receptionist booking">
                        Nova AI ✓
                    </span>
                </td>
            `;
            DOM.meetingsTableBody.appendChild(tr);
        });
    }

    // =========================================================================
    // Google Calendar Sync
    // =========================================================================
    async function triggerGoogleSync() {
        DOM.syncGoogleBtn.disabled = true;
        showToast("Synchronizing appointments with Google Calendar...", "info");

        try {
            const res = await fetch("/api/meetings/sync", { method: "POST" });
            const data = await res.json();
            if (res.ok && data.status === "success") {
                showToast(data.message || `Synced ${data.synced_count} appointment(s)!`, "success");
                loadDashboardData();
            } else {
                showToast(`Sync failed: ${data.message}`, "error");
            }
        } catch (err) {
            showToast(`Sync request failed: ${err.message}`, "error");
        } finally {
            DOM.syncGoogleBtn.disabled = false;
        }
    }

    // =========================================================================
    // Receptionist Call Activity Drawer
    // =========================================================================
    function openActivityDrawer() {
        if (!DOM.activityDrawerOverlay) return;
        DOM.activityDrawerOverlay.classList.add("open");
        loadDrawerCalls();
        loadDrawerNotes();
    }

    function closeActivityDrawer() {
        if (!DOM.activityDrawerOverlay) return;
        DOM.activityDrawerOverlay.classList.remove("open");
    }

    async function loadDrawerCalls() {
        try {
            const res = await fetch("/api/call-logs");
            const json = await res.json();
            if (json.status === "success") {
                if (DOM.drawerCallCount) DOM.drawerCallCount.textContent = json.count;
                if (DOM.topCallCountBadge) DOM.topCallCountBadge.textContent = json.count;
                renderDrawerCalls(json.data);
            }
        } catch (err) {
            console.error("Failed to load calls:", err);
        }
    }

    async function loadDrawerNotes() {
        try {
            const res = await fetch("/api/notes");
            const json = await res.json();
            if (json.status === "success") {
                DOM.drawerNoteCount.textContent = json.count;
                renderDrawerNotes(json.data);
            }
        } catch (err) {
            console.error("Failed to load notes:", err);
        }
    }

    function renderDrawerCalls(calls) {
        if (!DOM.drawerCallsList) return;
        DOM.drawerCallsList.innerHTML = "";

        if (calls.length === 0) {
            DOM.drawerCallsList.innerHTML = `<p style="color:var(--text-muted); font-size:0.85rem">No calls logged yet.</p>`;
            return;
        }

        calls.forEach(c => {
            const item = document.createElement("div");
            item.className = "drawer-item";
            item.innerHTML = `
                <div class="drawer-item-header">
                    <span class="drawer-caller">${escapeHtml(c.caller_name || 'Caller')}</span>
                    <span class="drawer-time">${escapeHtml(c.created_at || '')}</span>
                </div>
                ${c.phone_number ? `<div style="font-family:var(--font-mono); font-size:0.78rem; color:var(--teal-700); font-weight:600">Patient Phone: ${escapeHtml(c.phone_number)}</div>` : ''}
                <div class="drawer-summary">${escapeHtml(c.summary)}</div>
                ${c.action_items ? `<div class="drawer-actions">Action: ${escapeHtml(c.action_items)}</div>` : ''}
            `;
            DOM.drawerCallsList.appendChild(item);
        });
    }

    function renderDrawerNotes(notes) {
        if (!DOM.drawerNotesList) return;
        DOM.drawerNotesList.innerHTML = "";

        if (notes.length === 0) {
            DOM.drawerNotesList.innerHTML = `<p style="color:var(--text-muted); font-size:0.85rem">No recorded messages or notes.</p>`;
            return;
        }

        notes.forEach(n => {
            const item = document.createElement("div");
            item.className = "drawer-item";
            item.innerHTML = `
                <div class="drawer-item-header">
                    <span class="drawer-caller">${escapeHtml(n.caller_name || 'Caller')}</span>
                    <span class="drawer-time">${escapeHtml(n.created_at || '')}</span>
                </div>
                <div class="drawer-summary">${escapeHtml(n.content)}</div>
                <div style="font-size:0.75rem; color:var(--text-muted)">Category: ${escapeHtml(n.category || 'general')}</div>
            `;
            DOM.drawerNotesList.appendChild(item);
        });
    }

    // =========================================================================
    // Event Listeners
    // =========================================================================
    function setupEventListeners() {
        // Auto-refresh & manual reload
        if (DOM.autoRefreshBtn) DOM.autoRefreshBtn.addEventListener("click", toggleAutoRefresh);
        if (DOM.manualRefreshBtn) DOM.manualRefreshBtn.addEventListener("click", () => loadDashboardData());
        if (DOM.syncGoogleBtn) DOM.syncGoogleBtn.addEventListener("click", triggerGoogleSync);

        // Filter tabs
        if (DOM.filterTabsNav) {
            DOM.filterTabsNav.addEventListener("click", (e) => {
                const btn = e.target.closest(".filter-tab");
                if (!btn) return;
                document.querySelectorAll(".filter-tab").forEach(t => t.classList.remove("active"));
                btn.classList.add("active");
                state.activeFilter = btn.getAttribute("data-filter") || "all";
                fetchMeetings();
            });
        }

        // Search input with debounce
        let searchTimeout = null;
        if (DOM.searchInput) {
            DOM.searchInput.addEventListener("input", (e) => {
                const val = e.target.value.trim();
                state.searchQuery = val;
                if (DOM.clearSearchBtn) {
                    DOM.clearSearchBtn.style.display = val ? "block" : "none";
                }
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    fetchMeetings();
                }, 250);
            });
        }

        if (DOM.clearSearchBtn) {
            DOM.clearSearchBtn.addEventListener("click", () => {
                DOM.searchInput.value = "";
                state.searchQuery = "";
                DOM.clearSearchBtn.style.display = "none";
                fetchMeetings();
            });
        }

        // Date picker filter
        if (DOM.dateFilterInput) {
            DOM.dateFilterInput.addEventListener("change", (e) => {
                const val = e.target.value;
                state.dateFilter = val;
                if (DOM.clearDateBtn) {
                    DOM.clearDateBtn.style.display = val ? "inline-block" : "none";
                }
                fetchMeetings();
            });
        }

        if (DOM.clearDateBtn) {
            DOM.clearDateBtn.addEventListener("click", () => {
                DOM.dateFilterInput.value = "";
                state.dateFilter = "";
                DOM.clearDateBtn.style.display = "none";
                fetchMeetings();
            });
        }

        // View mode switcher
        if (DOM.viewCardsBtn) {
            DOM.viewCardsBtn.addEventListener("click", () => {
                state.viewMode = "cards";
                DOM.viewCardsBtn.classList.add("active");
                DOM.viewTableBtn.classList.remove("active");
                renderMeetings(state.meetings);
            });
        }

        if (DOM.viewTableBtn) {
            DOM.viewTableBtn.addEventListener("click", () => {
                state.viewMode = "table";
                DOM.viewTableBtn.classList.add("active");
                DOM.viewCardsBtn.classList.remove("active");
                renderMeetings(state.meetings);
            });
        }

        // Activity Drawer Triggers
        if (DOM.openActivityBtn) DOM.openActivityBtn.addEventListener("click", openActivityDrawer);
        if (DOM.closeDrawerBtn) DOM.closeDrawerBtn.addEventListener("click", closeActivityDrawer);
        if (DOM.activityDrawerOverlay) {
            DOM.activityDrawerOverlay.addEventListener("click", (e) => {
                if (e.target === DOM.activityDrawerOverlay) closeActivityDrawer();
            });
        }

        if (DOM.drawerCallsTab) {
            DOM.drawerCallsTab.addEventListener("click", () => {
                DOM.drawerCallsTab.classList.add("active");
                DOM.drawerNotesTab.classList.remove("active");
                DOM.drawerCallsList.style.display = "block";
                DOM.drawerNotesList.style.display = "none";
            });
        }

        if (DOM.drawerNotesTab) {
            DOM.drawerNotesTab.addEventListener("click", () => {
                DOM.drawerNotesTab.classList.add("active");
                DOM.drawerCallsTab.classList.remove("active");
                DOM.drawerNotesList.style.display = "block";
                DOM.drawerCallsList.style.display = "none";
            });
        }

        // Close drawer on Escape key
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") {
                closeActivityDrawer();
            }
        });
    }

    // =========================================================================
    // Utilities
    // =========================================================================
    function showToast(message, type = "info") {
        if (!DOM.toastContainer) return;
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;

        let iconSvg = '';
        if (type === 'success') {
            iconSvg = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`;
        } else if (type === 'error') {
            iconSvg = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
        } else {
            iconSvg = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="8"/></svg>`;
        }

        toast.innerHTML = `${iconSvg}<span>${escapeHtml(message)}</span>`;
        DOM.toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(10px)";
            toast.style.transition = "all 200ms ease";
            setTimeout(() => toast.remove(), 250);
        }, 3500);
    }

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Run on DOM ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
