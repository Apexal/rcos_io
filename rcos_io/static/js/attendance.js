let userIdField = document.getElementById("unverified_user");

/**
 * Called on "Verify" button click. Sends a message to verify an
 * RCS ID for attendance.
 */
let onVerify = () => {
    const userId = userIdField.value;
    
    if (userId === null) {
        return;
    }

    // verify user
}

/**
 * Called on "Close" button click. Sends a message to the server
 * to close the attendance room.
 */
let onClose = () => {
    
}