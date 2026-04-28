"""
Integration tests for the Mergington High School Activities API

Tests cover all API endpoints with happy path and error case scenarios.
Uses FastAPI's TestClient for integration testing.
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a TestClient instance for testing"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities state before each test to ensure test isolation"""
    # Store original state
    original_activities = {
        name: {
            "description": activity["description"],
            "schedule": activity["schedule"],
            "max_participants": activity["max_participants"],
            "participants": activity["participants"].copy()
        }
        for name, activity in activities.items()
    }
    
    yield
    
    # Restore original state after test completes
    for name in list(activities.keys()):
        if name in original_activities:
            activities[name]["participants"] = original_activities[name]["participants"].copy()


class TestRootRedirect:
    """Tests for GET / endpoint"""
    
    def test_root_redirects_to_static_index_html(self, client):
        """GET / should redirect to /static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """GET /activities should return all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        activities_data = response.json()
        
        # Verify all 9 activities are present
        expected_activities = {
            "Chess Club", "Programming Class", "Gym Class", "Basketball Team",
            "Tennis Club", "Art Studio", "Music Ensemble", "Debate Club", "Science Club"
        }
        assert set(activities_data.keys()) == expected_activities
    
    def test_get_activities_returns_correct_structure(self, client):
        """GET /activities response should have correct structure"""
        response = client.get("/activities")
        activities_data = response.json()
        
        # Check first activity structure
        chess_club = activities_data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)
    
    def test_get_activities_has_expected_participants(self, client):
        """GET /activities should return existing participants"""
        response = client.get("/activities")
        activities_data = response.json()
        
        # Chess Club should have initial participants
        assert "michael@mergington.edu" in activities_data["Chess Club"]["participants"]
        assert "daniel@mergington.edu" in activities_data["Chess Club"]["participants"]


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success_for_available_activity(self, client):
        """Student should successfully sign up for an available activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "student1@test.com"}
        )
        assert response.status_code == 200
        assert "Signed up" in response.json()["message"]
        assert "student1@test.com" in response.json()["message"]
    
    def test_signup_adds_participant_to_activity(self, client):
        """Signup should add student to activity's participants list"""
        student_email = "student2@test.com"
        
        # Sign up student
        client.post(
            "/activities/Programming Class/signup",
            params={"email": student_email}
        )
        
        # Verify student is in participants
        response = client.get("/activities")
        assert student_email in response.json()["Programming Class"]["participants"]
    
    def test_signup_nonexistent_activity_returns_404(self, client):
        """Signup to non-existent activity should return 404"""
        response = client.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "student3@test.com"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_duplicate_signup_returns_400(self, client):
        """Signing up twice to same activity should return 400"""
        student_email = "student4@test.com"
        activity = "Tennis Club"
        
        # First signup succeeds
        response1 = client.post(
            f"/activities/{activity}/signup",
            params={"email": student_email}
        )
        assert response1.status_code == 200
        
        # Second signup fails
        response2 = client.post(
            f"/activities/{activity}/signup",
            params={"email": student_email}
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]
    
    def test_signup_full_activity_returns_400(self, client):
        """Signup to full activity should return 400"""
        # Art Studio has max_participants=18 and 1 initial participant
        # We need to fill it up to capacity
        activity_name = "Art Studio"
        
        # Sign up students until activity is full
        # Art Studio has max 18, starts with 1, so we need 17 more
        for i in range(17):
            email = f"filler{i}@test.com"
            response = client.post(
                f"/activities/{activity_name}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Next signup should fail (activity now full)
        response = client.post(
            f"/activities/{activity_name}/signup",
            params={"email": "student_overflow@test.com"}
        )
        assert response.status_code == 400
        assert "full" in response.json()["detail"]


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success_for_enrolled_student(self, client):
        """Student should successfully unregister from activity"""
        student_email = "student5@test.com"
        activity = "Gym Class"
        
        # First sign up
        client.post(
            f"/activities/{activity}/signup",
            params={"email": student_email}
        )
        
        # Then unregister
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": student_email}
        )
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]
    
    def test_unregister_removes_participant_from_activity(self, client):
        """Unregister should remove student from activity's participants list"""
        student_email = "student6@test.com"
        activity = "Basketball Team"
        
        # Sign up student
        client.post(
            f"/activities/{activity}/signup",
            params={"email": student_email}
        )
        
        # Verify student is in participants
        response = client.get("/activities")
        assert student_email in response.json()[activity]["participants"]
        
        # Unregister student
        client.delete(
            f"/activities/{activity}/unregister",
            params={"email": student_email}
        )
        
        # Verify student is removed
        response = client.get("/activities")
        assert student_email not in response.json()[activity]["participants"]
    
    def test_unregister_nonexistent_activity_returns_404(self, client):
        """Unregister from non-existent activity should return 404"""
        response = client.delete(
            "/activities/Phantom Club/unregister",
            params={"email": "student7@test.com"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_unregister_not_enrolled_student_returns_400(self, client):
        """Unregister for non-enrolled student should return 400"""
        response = client.delete(
            "/activities/Chess Club/unregister",
            params={"email": "student_not_enrolled@test.com"}
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]
    
    def test_unregister_allows_resignment(self, client):
        """After unregistering, student should be able to sign up again"""
        student_email = "student8@test.com"
        activity = "Music Ensemble"
        
        # Sign up
        response1 = client.post(
            f"/activities/{activity}/signup",
            params={"email": student_email}
        )
        assert response1.status_code == 200
        
        # Unregister
        response2 = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": student_email}
        )
        assert response2.status_code == 200
        
        # Sign up again
        response3 = client.post(
            f"/activities/{activity}/signup",
            params={"email": student_email}
        )
        assert response3.status_code == 200


class TestCompleteWorkflow:
    """Integration tests for complete user workflows"""
    
    def test_student_signup_and_unregister_workflow(self, client):
        """Test complete workflow: view activities, sign up, verify, unregister"""
        student_email = "student9@test.com"
        activity = "Debate Club"
        
        # Step 1: Get all activities
        response = client.get("/activities")
        assert response.status_code == 200
        activities_list = response.json()
        assert activity in activities_list
        
        # Step 2: Sign up for activity
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": student_email}
        )
        assert response.status_code == 200
        
        # Step 3: Verify signup by getting activities
        response = client.get("/activities")
        assert student_email in response.json()[activity]["participants"]
        
        # Step 4: Unregister
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": student_email}
        )
        assert response.status_code == 200
        
        # Step 5: Verify unregister
        response = client.get("/activities")
        assert student_email not in response.json()[activity]["participants"]
    
    def test_multiple_students_same_activity(self, client):
        """Multiple students should be able to sign up for same activity"""
        activity = "Science Club"
        students = ["student10@test.com", "student11@test.com", "student12@test.com"]
        
        # All students sign up
        for student in students:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": student}
            )
            assert response.status_code == 200
        
        # Verify all are signed up
        response = client.get("/activities")
        participants = response.json()[activity]["participants"]
        for student in students:
            assert student in participants
