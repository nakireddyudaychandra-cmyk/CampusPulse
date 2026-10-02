from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import secrets

from database import get_connection, create_tables
from ai_engine import analyze_issue
from duplicate_detector import find_clusters


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(title="CampusPulse")


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATABASE
# ============================================================

create_tables()


# ============================================================
# ADMIN AUTHENTICATION
# ============================================================
# Demo credentials:
#
# Username: admin
# Password: admin123
#
# After successful login, the browser receives
# a temporary admin token.
#
# Admin-only requests must send:
#
# X-Admin-Key: <token>
#
# ============================================================

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

ADMIN_TOKEN = None


def require_admin(request: Request):

    global ADMIN_TOKEN

    token = request.headers.get("X-Admin-Key")

    if not ADMIN_TOKEN or token != ADMIN_TOKEN:

        raise HTTPException(
            status_code=401,
            detail="Admin authentication required"
        )

    return True


# ============================================================
# WEBSOCKET CONNECTION MANAGER
# ============================================================

class ConnectionManager:

    def __init__(self):

        self.active_connections = []


    async def connect(self, websocket: WebSocket):

        await websocket.accept()

        self.active_connections.append(websocket)


    def disconnect(self, websocket: WebSocket):

        if websocket in self.active_connections:

            self.active_connections.remove(websocket)


    async def broadcast(self, message):

        disconnected = []

        for websocket in self.active_connections:

            try:

                await websocket.send_json(message)

            except Exception:

                disconnected.append(websocket)


        for websocket in disconnected:

            self.disconnect(websocket)


manager = ConnectionManager()


# ============================================================
# PYDANTIC MODELS
# ============================================================

class AdminLogin(BaseModel):

    username: str
    password: str


class Issue(BaseModel):

    title: str
    description: str
    location: str


class StaffAssignment(BaseModel):

    staff_id: int


class StatusUpdate(BaseModel):

    status: str


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():

    return {
        "message": "Welcome to CampusPulse!",
        "status": "Server is running"
    }


# ============================================================
# ADMIN LOGIN
# ============================================================

@app.post("/admin/login")
def admin_login(data: AdminLogin):

    global ADMIN_TOKEN

    if (
        data.username != ADMIN_USERNAME
        or data.password != ADMIN_PASSWORD
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid admin username or password"
        )


    # Create a new temporary token

    ADMIN_TOKEN = secrets.token_urlsafe(32)


    return {

        "message": "Admin login successful",

        "token": ADMIN_TOKEN
    }


# ============================================================
# ADMIN LOGOUT
# ============================================================

@app.post("/admin/logout")
def admin_logout(request: Request):

    global ADMIN_TOKEN

    require_admin(request)

    ADMIN_TOKEN = None


    return {

        "message": "Admin logged out successfully"
    }


# ============================================================
# CHECK ADMIN LOGIN
# ============================================================

@app.get("/admin/check")
def admin_check(request: Request):

    require_admin(request)


    return {

        "authenticated": True
    }


# ============================================================
# CREATE ISSUE
# ============================================================

@app.post("/issues")
async def create_issue(issue: Issue):

    # --------------------------------------------------------
    # AI ANALYSIS
    # --------------------------------------------------------

    category, priority = analyze_issue(
        issue.title,
        issue.description
    )


    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    connection = get_connection()

    cursor = connection.cursor()


    # --------------------------------------------------------
    # INSERT ISSUE
    # --------------------------------------------------------

    cursor.execute(
        """
        INSERT INTO issues
        (
            title,
            description,
            location,
            category,
            priority,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            issue.title,
            issue.description,
            issue.location,
            category,
            priority,
            "OPEN"
        )
    )


    connection.commit()

    issue_id = cursor.lastrowid

    connection.close()


    # --------------------------------------------------------
    # REAL-TIME NOTIFICATION
    # --------------------------------------------------------

    await manager.broadcast({

        "event": "NEW_ISSUE",

        "issue_id": issue_id,

        "message": "A new issue has been reported"
    })


    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {

        "message": "Issue reported successfully",

        "issue_id": issue_id,

        "category": category,

        "priority": priority,

        "status": "OPEN"
    }


# ============================================================
# GET ALL ISSUES
# ============================================================
#
# Kept public because the student "My Issues" page
# also needs to display the reported issues.
#
# ============================================================

@app.get("/issues")
def get_issues():

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT *
        FROM issues
        ORDER BY id DESC
        """
    )


    issues = cursor.fetchall()

    connection.close()


    return [
        dict(issue)
        for issue in issues
    ]


# ============================================================
# GET SINGLE ISSUE
# ============================================================

@app.get("/issues/{issue_id}")
def get_single_issue(issue_id: int):

    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT *
        FROM issues
        WHERE id = ?
        """,
        (issue_id,)
    )


    issue = cursor.fetchone()

    connection.close()


    if issue is None:

        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )


    return dict(issue)


# ============================================================
# GET ALL STAFF
# ============================================================
# ADMIN ONLY
# ============================================================

@app.get("/staff")
def get_staff(request: Request):

    require_admin(request)


    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT *
        FROM staff
        ORDER BY id
        """
    )


    staff = cursor.fetchall()

    connection.close()


    return [
        dict(member)
        for member in staff
    ]


# ============================================================
# ASSIGN STAFF TO ISSUE
# ============================================================
# ADMIN ONLY
# ============================================================

@app.put("/issues/{issue_id}/assign")
async def assign_staff(
    issue_id: int,
    assignment: StaffAssignment,
    request: Request
):

    require_admin(request)


    connection = get_connection()

    cursor = connection.cursor()


    # --------------------------------------------------------
    # CHECK ISSUE
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT *
        FROM issues
        WHERE id = ?
        """,
        (issue_id,)
    )


    issue = cursor.fetchone()


    if issue is None:

        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )


    # --------------------------------------------------------
    # CHECK STAFF
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT *
        FROM staff
        WHERE id = ?
        """,
        (assignment.staff_id,)
    )


    staff = cursor.fetchone()


    if staff is None:

        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Staff member not found"
        )


    # --------------------------------------------------------
    # ASSIGN STAFF
    # --------------------------------------------------------

    cursor.execute(
        """
        UPDATE issues
        SET assigned_staff_id = ?
        WHERE id = ?
        """,
        (
            assignment.staff_id,
            issue_id
        )
    )


    connection.commit()


    # --------------------------------------------------------
    # GET UPDATED ISSUE
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT *
        FROM issues
        WHERE id = ?
        """,
        (issue_id,)
    )


    updated_issue = cursor.fetchone()

    connection.close()


    issue_data = dict(updated_issue)

    staff_data = dict(staff)


    # --------------------------------------------------------
    # REAL-TIME NOTIFICATION
    # --------------------------------------------------------

    await manager.broadcast({

        "event": "STAFF_ASSIGNED",

        "issue": issue_data
    })


    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {

        "message": "Staff assigned successfully",

        "issue": issue_data,

        "assigned_staff_name":
            staff_data["name"],

        "assigned_staff_specialization":
            staff_data["specialization"]
    }


# ============================================================
# UPDATE ISSUE STATUS
# ============================================================
# ADMIN ONLY
# ============================================================

@app.put("/issues/{issue_id}")
async def update_issue_status(
    issue_id: int,
    request: Request
):

    require_admin(request)


    status = None


    # --------------------------------------------------------
    # TRY JSON BODY
    # --------------------------------------------------------

    try:

        body = await request.json()

        if isinstance(body, dict):

            status = body.get("status")

    except Exception:

        pass


    # --------------------------------------------------------
    # ALSO SUPPORT QUERY PARAMETER
    # Example:
    #
    # /issues/5?status=RESOLVED
    #
    # --------------------------------------------------------

    if not status:

        status = request.query_params.get(
            "status"
        )


    # --------------------------------------------------------
    # VALIDATE STATUS
    # --------------------------------------------------------

    if not status:

        raise HTTPException(
            status_code=400,
            detail="Status is required"
        )


    status = status.upper()


    allowed_statuses = [

        "OPEN",

        "IN PROGRESS",

        "RESOLVED"
    ]


    if status not in allowed_statuses:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid status. Use OPEN, "
                "IN PROGRESS, or RESOLVED."
            )
        )


    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    connection = get_connection()

    cursor = connection.cursor()


    # --------------------------------------------------------
    # CHECK ISSUE
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT *
        FROM issues
        WHERE id = ?
        """,
        (issue_id,)
    )


    issue = cursor.fetchone()


    if issue is None:

        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )


    # --------------------------------------------------------
    # UPDATE STATUS
    # --------------------------------------------------------

    cursor.execute(
        """
        UPDATE issues
        SET status = ?
        WHERE id = ?
        """,
        (
            status,
            issue_id
        )
    )


    connection.commit()


    # --------------------------------------------------------
    # GET UPDATED ISSUE
    # --------------------------------------------------------

    cursor.execute(
        """
        SELECT *
        FROM issues
        WHERE id = ?
        """,
        (issue_id,)
    )


    updated_issue = cursor.fetchone()

    connection.close()


    issue_data = dict(updated_issue)


    # --------------------------------------------------------
    # REAL-TIME UPDATE
    # --------------------------------------------------------

    await manager.broadcast({

        "event": "STATUS_UPDATED",

        "issue": issue_data
    })


    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {

        "message": "Issue status updated",

        "issue_id": issue_id,

        "status": status
    }


# ============================================================
# WEBSOCKET
# ============================================================

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket
):

    await manager.connect(websocket)


    try:

        while True:

            await websocket.receive_text()


    except WebSocketDisconnect:

        manager.disconnect(websocket)


    except Exception:

        manager.disconnect(websocket)


# ============================================================
# DUPLICATE / RELATED ISSUE DETECTION
# ============================================================
# ADMIN ONLY
# ============================================================

@app.get("/clusters")
def get_issue_clusters(
    request: Request
):

    require_admin(request)


    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        SELECT *
        FROM issues
        ORDER BY id DESC
        """
    )


    issues = cursor.fetchall()

    connection.close()


    # --------------------------------------------------------
    # CONVERT DATABASE ROWS TO DICTIONARIES
    # --------------------------------------------------------

    issues = [

        dict(issue)

        for issue in issues
    ]


    # --------------------------------------------------------
    # FIND RELATED ISSUES
    # --------------------------------------------------------

    clusters = find_clusters(issues)


    result = []


    for cluster in clusters:

        if not cluster:

            continue


        first_issue = cluster[0]


        result.append({

            "location":
                first_issue["location"],

            "category":
                first_issue["category"],

            "report_count":
                len(cluster),

            "issues":
                cluster
        })


    return result