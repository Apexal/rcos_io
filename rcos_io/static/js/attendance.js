let user_id_field = document.getElementById("unverified_user");
let verification_status = document.getElementById("verification_status");

/**
 * Called on "Verify" button click. Sends a message to verify an
 * RCS ID for attendance.
 */
let onVerify = (meeting_id) => {
    const user_id = user_id_field.value;
    
    if (user_id === null || user_id.length == 0) {
        return;
    }

    fetch('/meetings/attendance/verify', {
        method: 'POST',
        credentials: 'include',
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            user_id, meeting_id
        })
    })
    .then(response => response.text())
    .then(data => {
        verification_status.innerText = data
    });
}