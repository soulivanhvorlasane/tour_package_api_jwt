# Tour Package API Documentation (JWT)

This document provides a comprehensive overview of the REST API endpoints provided by the `tour_package_api_jwt` module. All requests and responses are in `application/json` format.

## Authentication
Most endpoints require a valid JSON Web Token (JWT) passed in the `Authorization` HTTP header:
`Authorization: Bearer <YOUR_JWT_TOKEN>`

Tokens are valid for 1 hour by default and can be refreshed using the `/api/refresh` endpoint.

---

## 1. Authentication & Users

### User Login
Authenticate a user and retrieve a JWT token.
* **Endpoint**: `POST /api/login`
* **Payload**:
  ```json
  {
      "params": {
          "username": "user@example.com",
          "password": "yourpassword"
      }
  }
  ```
* **Success Response**: `{"result": {"token": "eyJhbG..."}}`
* **Error Response**: `{"result": {"error": "Invalid credentials"}}`

### User Registration
Register a new customer account (automatically assigns Portal access) and returns a JWT token.
* **Endpoint**: `POST /api/user/register`
* **Payload**:
  ```json
  {
      "params": {
          "name": "John Doe",
          "email": "john@example.com",
          "password": "securepassword"
      }
  }
  ```
* **Success Response**: `{"result": {"success": true, "token": "eyJhb...", "user_id": 15}}`

### Token Refresh
Generate a new JWT token using an existing valid token.
* **Endpoint**: `POST /api/refresh`
* **Headers**: `Authorization: Bearer <TOKEN>`
* **Success Response**: `{"result": {"token": "eyJhb_NEW_TOKEN..."}}`

### User Logout
Invalidate the current session and add the token to the blacklist database.
* **Endpoint**: `POST /api/user/logout`
* **Headers**: `Authorization: Bearer <TOKEN>`
* **Success Response**: `{"result": {"success": true, "message": "Logged out successfully..."}}`

---

## 2. Profile Management

### Get User Profile
Fetch basic profile information and avatar URL.
* **Endpoint**: `POST /api/user/profile`  *(GET also supported)*
* **Headers**: `Authorization: Bearer <TOKEN>`
* **Success Response**:
  ```json
  {
      "result": {
          "id": 15,
          "name": "John Doe",
          "email": "john@example.com",
          "phone": "+1234567890",
          "profile_image": "http://localhost:8069/web/image/123"
      }
  }
  ```

### Update Profile Image
Upload a new avatar/profile picture.
* **Endpoint**: `POST /api/user/profile/image`
* **Headers**: `Authorization: Bearer <TOKEN>`
* **Payload**:
  ```json
  {
      "params": {
          "image": "iVBORw0KGgoAAAANSUhEUgAA..." // Base64 string without data prefix
      }
  }
  ```
* **Success Response**: `{"result": {"success": true, "profile_image": "http://..."}}`

---

## 3. Tour Packages

### List All Active Packages
Fetch a list of all tour packages currently active and available.
* **Endpoint**: `POST /api/packages` *(GET also supported)*
* **Success Response**:
  ```json
  {
      "result": [
          {
              "id": 1,
              "name": "Vang Vieng Adventure",
              "category": "Adventure",
              "price": 150.0,
              "duration": 3,
              "availability_status": "available",
              "cover_image": "http://localhost:8069/web/image/tour.package/1/cover_image"
          }
      ]
  }
  ```

### Get Package Detail
Fetch full details for a specific package, including image gallery and calendar dates.
* **Endpoint**: `POST /api/package/detail`
* **Payload**:
  ```json
  {
      "params": {
          "package_id": 1
      }
  }
  ```
* **Success Response**:
  ```json
  {
      "result": {
          "id": 1,
          "name": "Vang Vieng Adventure",
          "description": "A thrilling 3-day adventure...",
          "price": 150.0,
          "calendars": [
              {
                  "id": 5,
                  "date_start": "2026-08-01",
                  "date_end": "2026-08-03",
                  "state": "open",
                  "remaining_seats": 12
              }
          ],
          "gallery": ["http://localhost:8069/web/image/22", "..."]
      }
  }
  ```

---

## 4. Bookings & Calendar

### Book a Package
Create a new booking for a specific calendar slot.
* **Endpoint**: `POST /api/package/book`
* **Headers**: `Authorization: Bearer <TOKEN>`
* **Payload**:
  ```json
  {
      "params": {
          "calendar_id": 5,
          "seats": 2
      }
  }
  ```
* **Success Response**: `{"result": {"success": true, "booking_id": 45, "message": "Booking created successfully"}}`
* **Error Response**: `{"result": {"error": "Not enough seats available"}}`

### My Bookings List
Retrieve a list of all bookings associated with the authenticated user.
* **Endpoint**: `POST /api/user/bookings` *(GET also supported)*
* **Headers**: `Authorization: Bearer <TOKEN>`
* **Success Response**:
  ```json
  {
      "result": [
          {
              "id": 45,
              "name": "BKG0045",
              "state": "draft",
              "start_date": "2026-08-01",
              "end_date": "2026-08-03"
          }
      ]
  }
  ```

### My Calendar Events
Retrieve the user's bookings formatted specifically for FullCalendar/frontend calendar plotting.
* **Endpoint**: `POST /api/user/calendar` *(GET also supported)*
* **Headers**: `Authorization: Bearer <TOKEN>`
* **Success Response**:
  ```json
  {
      "result": [
          {
              "title": "Vang Vieng Adventure",
              "start": "2026-08-01",
              "end": "2026-08-04",
              "backgroundColor": "#ffc107",
              "extendedProps": {
                  "booking_id": 45,
                  "seats": 2,
                  "status": "Draft"
              }
          }
      ]
  }
  ```
