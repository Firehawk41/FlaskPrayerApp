

document.addEventListener('DOMContentLoaded', function() {
    // Get checkboxes and action buttons
    const checkboxes = document.querySelectorAll('input[name="selectedPrayers"]');
    const markAnsweredBtn = document.getElementById('markAnsweredBtn');
    const markPendingBtn = document.getElementById('markPendingBtn');
    const markPrayedBtn = document.getElementById('markPrayedBtn');
    const deleteBtn = document.getElementById('deleteBtn');

    // Enable/disable action buttons based on checkbox selection
    checkboxes.forEach(function(checkbox) {
        checkbox.addEventListener('change', function() {
            const checkedCheckboxes = document.querySelectorAll('input[name="selectedPrayers"]:checked');
            const numChecked = checkedCheckboxes.length;
            const disabled = numChecked === 0;

            markAnsweredBtn.disabled = disabled;
            markPendingBtn.disabled = disabled;
            markPrayedBtn.disabled = disabled;
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


    markPrayedBtn.addEventListener('click', function() {
        handlePrayerAction('mark_prayed');
    });


    deleteBtn.addEventListener('click', function() {
        handlePrayerAction('delete_prayer');
    });

    // Function to handle prayer action
    function handlePrayerAction(action) {
        const checkedCheckboxes = document.querySelectorAll('input[name="selectedPrayers"]:checked');
        checkedCheckboxes.forEach(function(checkbox) {
            const prayerId = checkbox.value;

            // Make AJAX request
            const xhr = new XMLHttpRequest();
            xhr.open('POST', `/${action}/${prayerId}`, true);
            xhr.setRequestHeader('Content-Type', 'application.json');
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

/*
function toggleAddPrayerForm() {
    var formRow = document.getElementById('addPrayerForm');
    formRow.style.display = formRow.style.display === 'none' ? 'table-row' : 'none';
}
function addPrayer(event) {
    //Prevent the default form submission behavior
    event.preventDefault();

    var title = document.getElementById('newPrayerTitle').value;
    var description = document.getElementById('newPrayerDescription').value;
    var tag = document.querySelector('select[name="tag"]').value;

    // Create a new FormData object to send the form data
    var formData = new FormData();
    formData.append('title', title);
    formData.append('description', description);
    formData.append('tag', tag);

    //Log the values of title and description to the console
    console.log('Title:', title);
    console.log('Description:', description);
    console.log('Tag:' + tag);

    // Send a POST request to the server using AJAX
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/add_prayer', true);

    xhr.onload = function () {
        if (xhr.status === 200) {
            window.location.reload();
        } else {
            console.error('Failed to add prayer. Status: ' + xhr.status);
        }
    };
    
    xhr.onerror = function () {
        console.error('Failed to send request.');
    };

    xhr.send(formData);
}
*/