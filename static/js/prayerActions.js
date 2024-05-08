

document.addEventListener('DOMContentLoaded', function() {
    // Get checkboxes and action buttons
    const checkboxes = document.querySelectorAll('input[name="selectedPrayers"]');
    const markAnsweredBtn = document.getElementById('markAnsweredBtn');
    const markPendingBtn = document.getElementById('markPendingBtn');
    const deleteBtn = document.getElementById('deleteBtn');

    // Enable/disable action buttons based on checkbox selection
    checkboxes.forEach(function(checkbox) {
        checkbox.addEventListener('change', function() {
            const checkedCheckboxes = document.querySelectorAll('input[name="selectedPrayers"]:checked');
            const numChecked = checkedCheckboxes.length;
            const disabled = numChecked === 0;

            markAnsweredBtn.disabled = disabled;
            markPendingBtn.disabled = disabled;
            deleteBtn.disabled = disabled;
        });
    });

    // Event listeners for action buttons
    markAnsweredBtn.addEventListener('click', function() {
        handlePrayerAction('mark_answered');
    });

    markPendingBtn.addEventListener('click', function() {
        handlePrayerAction('mark_pending');
    });

    deleteBtn.addEventListener('click', function() {
        handlePrayerAction('delete_prayer');
    });

    // Get the CSRF token from a hidden input field
    const csrfToken = document.querySelector('input[name="csrf_token"]').value;

    // Function to handle prayer action
    function handlePrayerAction(action) {
        const checkedCheckboxes = document.querySelectorAll('input[name="selectedPrayers"]:checked');
        checkedCheckboxes.forEach(function(checkbox) {
            const prayerId = checkbox.value;

            // Make AJAX request with CSRF token
            const xhr = new XMLHttpRequest();
            xhr.open('POST', `/${action}/${prayerId}`, true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.setRequestHeader('X-CSRFToken', csrfToken);
            xhr.onreadystatechange = function() {
                if (xhr.readyState === XMLHttpRequest.DONE) {
                    // Handle response
                    if (xhr.status === 200) {
                        window.location.reload();
                        console.log('Prayer action successful');
                    } else {
                        console.error('Error:', xhr.status);
                        //Handle error
                    
                    }
                }
            };
            xhr.send();
        });
    }


});
