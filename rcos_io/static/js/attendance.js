let user_id_field = document.getElementById("unverified_user");
let verification_status = document.getElementById("verification_status");

/**
 * Given a room code and meeting ID, close a room for attendance. 
 * @param {string} code 
 * @param {string} meeting_id 
 */
let onClose = (code, meeting_id) => {
    // /meetings/<meeting_id>/close?=ABCDE
    fetch('/meetings/' + meeting_id + '/close?code=' + code, {
        method: 'POST',
        credentials: 'include',
        headers: {
            "Content-Type": "application/json"
        }
    })
    .then(response => response.text())
    .then(data => {
        window.location.replace(data);
    });
}

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
    })
    .then(response => response.text())
    .then(data => {
        verification_status.innerText = data
    });
}