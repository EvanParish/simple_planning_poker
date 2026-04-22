
# **Product Requirements & Technical Specification: Simple Planning Poker**

## **Part I: Product Requirements**

### **1. Overview & Objective**
Create a frictionless, web-based planning poker application that requires no user accounts or persistent backend storage. The goal is to allow agile teams to quickly spin up a session, estimate tasks using a Fibonacci sequence, and seamlessly transition between rounds of voting. 

### **2. Tech Stack**
* **Framework:** Python with NiceGUI.
* **State Management:** In-memory WebSocket state handling. The room and its data are created in memory when the first user joins and completely destroyed when the last user disconnects (post-grace period).

### **3. User Roles & Permissions**
* **Moderator:** The user who creates the room.
    * *Permissions:* Can vote, toggle Observer status, trigger "Reveal Cards" (manual override), and trigger "Reset Round."
* **Participant:** Any user who joins via the room URL/Code. 
    * *Permissions:* Can vote, and can toggle their own "Observer" status.
* **Observer:** A Participant or Moderator who has toggled on the "Observer" status. 
    * *Permissions:* Cannot vote (voting cards are disabled/hidden). Simply watches the state of the room. Persistent across rounds until toggled off.

### **4. Game Rules & Logic**
* **Available Cards:** Fibonacci sequence (1, 2, 3, 5, 8, 13, 21), plus `?` (Unsure) and `☕` (Break).
* **Changing Votes:** Users can change their pending vote as many times as they want by selecting a different card, up until the cards are revealed. Once revealed, voting is locked.
* **Average Calculation:** Displays the exact mathematical average of all submitted numeric votes. `?` and `☕` are excluded from the denominator and the calculation.
* **Vote Distribution:** When cards are revealed, the UI displays a count of each card value chosen (e.g., `5 × 3`, `8 × 2`), sorted by frequency descending.
* **Auto-Reveal:** The system constantly checks the number of submitted votes against the number of active, non-observer users. If `votes == (total_users - observers)`, the cards are automatically revealed.
* **Timer:** The Moderator can start a countdown timer before or during voting. 
    * **Presets & Custom:** Preset buttons (1m, 2m, 3m, 5m) and a custom input field (1–3600 seconds) are available.
    * **Visibility:** All participants see a live countdown (mm:ss) synced to a server-side deadline.
    * **Auto-Reveal on Expiry:** When the timer reaches zero, votes are automatically revealed.
    * **Cancellation:** The Moderator can cancel a running timer at any time.
    * **Interactions:** The timer stops automatically when Auto-Reveal fires (all votes in), when the Moderator manually reveals cards, or when the round is reset.
    * **Sound:** A subtle ascending chime plays when the timer starts; a descending chime plays when it finishes. Sounds are generated via the Web Audio API (no audio files).
* **Late Joiners:** If a user joins the room *after* the cards have been revealed for the current ticket, they will see the read-only results of that finished round. They must wait for the Moderator to reset the round before they can participate.
* **Name Collisions:** If a user attempts to join a room with a display name that is already actively in the room, the UI will block entry and prompt them to append an initial or choose a different name.

### **5. Connection & State Resilience**
* **Silent Reconnection:** Upon joining, users are assigned a lightweight local storage token (or session cookie). If they refresh or briefly lose connection, this token silently authenticates them back into their active persona without requiring them to re-enter their name.
* **Disconnect Grace Period:** If a WebSocket disconnects, the user is visually flagged as "Reconnecting..." to the rest of the room. 
* **State Updates:** Auto-Reveal and Moderator Inheritance are paused for this specific user's status during a 30-second grace period. If the user does not reconnect within 30 seconds, they are removed from the room, their pending vote is destroyed, and Moderator status is passed to the oldest remaining Participant if necessary.

### **6. Core User Flows**
1.  **Creating a Room:** User arrives at the homepage, enters their display name, and clicks "Create Room." They are assigned Moderator status and routed to a room with a randomly generated 6-digit alphanumeric code.
2.  **Joining a Room:** User arrives at the homepage, enters their display name and the 6-digit code (or clicks a direct share link which pre-fills the code), and joins the room. When the Room Code field contains a value (either pre-filled via link or typed manually), the "Create Room" button is hidden so the user is guided toward joining the existing room.
3.  **Voting Loop:** * Moderator announces the ticket.
    * Participants click a card. UI indicates a "check mark" or "card face down" next to their name to show they have voted.
    * Cards are revealed (either via Auto-Reveal or the Moderator clicking "Reveal Cards").
    * UI displays all individual votes and the calculated average.
    * Moderator clicks "Reset Round" to clear all current votes and unlock the board for the next ticket.

### **7. UI/UX Layout (Mobile-First)**
* **Header / Top Bar:**
    * Displays the 6-digit Room Code with a quick "Copy Invite Link" icon.
    * Displays Moderator controls (if applicable): "Reveal Cards" and "Reset Round" buttons.
    * A dark/light mode toggle button (sun icon in dark mode, moon icon in light mode) is fixed to the top-right corner. The user's theme preference is persisted in browser storage.
* **Topic Area (below header):**
    * An optional text area where the Moderator can describe the current issue being estimated. Only the Moderator can edit this field; Participants see a read-only view.
    * GitHub issue URLs (including GitHub Enterprise and project board URLs) are automatically shortened to `repo#number` format and rendered as clickable links.
* **Voting Cards (below topic):**
    * A horizontally wrapped row of the voting cards (Fibonacci, `?`, `☕`). Placed above the user list for visibility.
* **Timer Controls (below topic, above cards):**
    * **Moderator view (no timer running):** Preset duration buttons (1m, 2m, 3m, 5m), a custom seconds input, and a "Start" button.
    * **All users (timer running):** A centered timer icon with a live mm:ss countdown. The Moderator also sees a cancel (×) button.
    * **Hidden** when votes are already revealed.
* **Results Banner (below cards, when revealed):**
    * Displays the **Calculated Average** and the **Vote Distribution** (count per card value).
* **Observer Toggle (below results):**
    * An "Observer Mode" checkbox, placed above the user list.
* **Main Content Area (The Table):**
    * A clean, vertical list of all users currently in the room, sorted by join time.
    * Each row displays: User's Name, a "Mod" badge (if moderator), and their current status (e.g., "Thinking...", "✓ Voted", "Reconnecting...", "Observer", or the actual card value once revealed).

---

## **Part II: Technical Implementation & AI Instructions**

### **1. Explicit Exclusions (Strict Guidelines)**
* **NO External Databases:** Do not use SQLite, PostgreSQL, MongoDB, Redis, etc. All state must be managed in-memory using Python data structures.
* **NO Authentication Systems:** Do not implement OAuth, passwords, or persistent user accounts. Identity is tied strictly to the session/local storage token for the duration of the room.
* **NO External CSS Frameworks:** Rely exclusively on NiceGUI's built-in Tailwind CSS integration for styling. Keep custom CSS to an absolute minimum.

### **2. Target File Structure**
Do not place all code in a single file. Adhere to the following modular structure:
* `main.py` - Application entry point, NiceGUI configuration, and route definitions.
* `models.py` - Pydantic or Python Dataclasses defining the shape of `User` and `Room`.
* `state.py` - The in-memory state manager (e.g., a dictionary mapping room codes to `Room` objects) and core logic functions (calculate average, check auto-reveal).
* `ui.py` - Reusable NiceGUI UI components (e.g., `voting_card()`, `user_row()`, `moderator_controls()`).
* `Dockerfile` - Container configuration.
* `docker-compose.yml` - Orchestration file.
* `pyproject.toml` - Project metadata and dependencies (managed via `uv`).

### **3. Explicit Data Models**
Use Python `dataclasses` (or Pydantic) to strictly type the state. Recommended baseline:

* **User Model:**
    * `client_id` (str): Unique identifier (UUID) generated upon joining (stored in local storage/cookie).
    * `name` (str): Display name.
    * `vote` (str | None): The current selected card.
    * `is_observer` (bool): Toggled state.
    * `is_moderator` (bool): Moderator status.
    * `is_connected` (bool): WebSocket status.
    * `last_seen` (float): Timestamp for managing the 30-second grace period.
    * `joined_at` (float): Timestamp to determine "oldest participant" for moderator inheritance.
    * `connect_epoch` (int): Monotonically increasing counter used to invalidate stale disconnect timers after a reconnect.

* **Room Model:**
    * `room_code` (str): 6-digit alphanumeric ID.
    * `users` (dict[str, User]): Mapping of `client_id` to `User` objects.
    * `is_revealed` (bool): Current phase of the voting round.
    * `current_topic` (str): Moderator-editable text describing the issue under estimation.
    * `timer_end` (float | None): Unix timestamp when the active countdown timer expires. `None` when no timer is running.

### **4. Implementation Phases (For AI Prompting)**
AI Assistant: Execute this build sequentially. Do not move to the next phase until the current phase is fully functional and verified by the user.

* **Phase 1: Foundation & Scaffolding**
    * Use python 3.14 with `uv`
      * Use `pyproject.toml` for app dependencies using `uv` and python 3.14
      * The `.python-version` file tells you what
    * Set up `Dockerfile`, and `docker-compose.yml`.
    * Create the basic file structure.
    * Build the landing page (`/`) in `main.py` with NiceGUI inputs for Name and Room Code (or "Create Room" button).
* **Phase 2: State Management & Routing**
    * Implement `models.py` and the in-memory store in `state.py`.
    * Build the logic for generating a room code, creating a room, joining a room, and handling duplicate names.
    * Implement the local storage client ID to allow users to reconnect.
    * Route users to `/room/{room_code}` upon successful entry.
* **Phase 3: The Voting Loop & UI**
    * Build the Room UI (`ui.py`): the header, the vertical user list, and the voting cards.
    * Implement real-time WebSocket syncing (when a user joins, toggles observer, or clicks a card, the UI updates for everyone).
    * Implement Moderator controls ("Reveal", "Reset") and the Observer toggle.
* **Phase 4: Advanced Logic & Edge Cases**
    * Implement the Auto-Reveal logic.
    * Implement the mathematical average calculation (ignoring `?` and `☕`).
    * Implement the Late Joiner logic (read-only state if joined while `is_revealed == True`).
* **Phase 5: Connection Resilience**
    * Implement the 30-second disconnect grace period.
    * The global page timeout on all pages should be extended from the default to 10 seconds to avoid premature 5xx errors.
    * Implement the visual "Reconnecting..." state.
    * Implement Moderator Inheritance (transferring moderator to the oldest `joined_at` participant if the moderator fully disconnects).
* **Phase 6: Topic Area, Vote Counts & UI Cleanup**
    * Place the voting cards above the user list.
    * Update the Observer Mode toggle to a checkbox, placed above the user list.
    * Display a count of each card value chosen when votes are revealed.
    * Add an optional topic text area (above the user list) where the moderator can describe the current issue. Only the moderator can modify this field.
    * GitHub issue URLs are automatically shortened to a clickable `repo#number` format (supports github.com, GitHub Enterprise, and project board URLs).
* **Phase 7: Storage Cleanup & Dark Theme Toggle**
    * On startup, remove the `.nicegui` storage directory to ensure no stale artifacts from previous runs persist.
    * Create a dark/light mode theme toggle with a sun/moon icon. The user's preference is persisted in browser storage.
