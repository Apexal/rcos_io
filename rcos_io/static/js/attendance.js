let user_id_field = document.getElementById("unverified_user");

/**
 * Called on "Verify" button click. Sends a message to verify an
 * RCS ID for attendance.
 */
let onVerify = () => {
    const user_id = user_id_field.value;
    
    if (user_id === null || user_id.length == 0) {
        return;
    }

    fetch('/attendance/verify', {
        method: 'POST',
        credentials: 'include',
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            user_id
        })
    });
}