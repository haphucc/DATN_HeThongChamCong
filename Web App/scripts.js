function openTab(evt, tabName) {
    var i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }
    tablinks = document.getElementsByClassName("tablinks");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";

    // Lưu trạng thái tab hiện tại vào sessionStorage
    sessionStorage.setItem('activeTab', tabName);

    // Khi mở tab Timekeeping, hiển thị bảng mặc định với 3 cột
    if (tabName === 'Timekeeping') {
        renderDefaultTimekeepingTable();
    }
}

function filterEmployees() {
    var idFilter = document.getElementById("employee-id-filter").value.toLowerCase();
    var nameFilter = document.getElementById("employee-name-filter").value.toLowerCase();
    var positionFilter = document.getElementById("employee-position-filter").value.toLowerCase();

    var table = document.getElementById("employeesTable");
    var rows = table.getElementsByTagName("tr");

    for (var i = 1; i < rows.length; i++) {
        var cells = rows[i].getElementsByTagName("td");
        var id = cells[0].textContent.toLowerCase();
        var name = cells[1].textContent.toLowerCase();
        var position = cells[2].textContent.toLowerCase();

        var idMatch = id.includes(idFilter);
        var nameMatch = name.includes(nameFilter);
        var positionMatch = position.includes(positionFilter);

        if (idMatch && nameMatch && positionMatch) {
            rows[i].style.display = "";
        } else {
            rows[i].style.display = "none";
        }
    }
}

// Hàm hiển thị bảng mặc định với 3 cột khi mở tab Timekeeping
function renderDefaultTimekeepingTable() {
    var tableHead = document.getElementById("tableHead");
    var tableBody = document.getElementById("tableBody");

    // Tạo tiêu đề bảng với 3 cột
    var headRow = `<tr>
        <th>Mã NV</th>
        <th>Tên</th>
        <th>Vị trí</th>
    </tr>`;
    tableHead.innerHTML = headRow;

    // Tạo dữ liệu cho bảng
    tableBody.innerHTML = "";
    for (var key in timekeepingData) {
        var entry = timekeepingData[key];
        var employeeId = entry.employee_id;
        var name = entry.name;
        var position = entry.position;

        var newRow = `<tr>
            <td>${employeeId}</td>
            <td>${name}</td>
            <td>${position}</td>
        </tr>`;
        tableBody.innerHTML += newRow;
    }

    applyFilters();
}

function renderTable(month, year) {
    var tableHead = document.getElementById("tableHead");
    var tableBody = document.getElementById("tableBody");

    // Tạo tiêu đề bảng với đầy đủ cột
    var headRow = `<tr>
        <th>Mã NV</th>
        <th>Tên</th>
        <th>Vị trí</th>
        <th>Ngày</th>`;
    for (var i = 1; i <= maxChecks; i++) {
        headRow += `<th>Check${i}</th>`;
    }
    headRow += `</tr>`;
    tableHead.innerHTML = headRow;

    // Tạo dữ liệu cho bảng
    tableBody.innerHTML = "";
    for (var key in timekeepingData) {
        var entry = timekeepingData[key];
        var employeeId = entry.employee_id;
        var name = entry.name;
        var position = entry.position;
        var date = entry.date;

        // Lọc theo tháng và năm
        var dateParts = date.split('/');
        var entryMonth = dateParts[1];
        var entryYear = dateParts[2];
        if ((month && entryMonth !== month) || (year && entryYear !== year)) {
            continue;
        }

        var newRow = `<tr>
            <td>${employeeId}</td>
            <td>${name}</td>
            <td>${position}</td>
            <td>${date}</td>`;
        for (var i = 0; i < maxChecks; i++) {
            var time = entry.times[i] || '-';
            newRow += `<td>${time}</td>`;
        }
        newRow += `</tr>`;
        tableBody.innerHTML += newRow;
    }

    applyFilters();
}

function applyFilters() {
    var monthFilter = document.getElementById("timekeeping-month").value;
    var yearFilter = document.getElementById("timekeeping-year").value;
    var idFilter = document.getElementById("timekeeping-id-filter").value.toLowerCase();
    var nameFilter = document.getElementById("timekeeping-name-filter").value.toLowerCase();
    var positionFilter = document.getElementById("timekeeping-position-filter").value.toLowerCase();

    var table = document.getElementById("timekeepingTable");
    var rows = table.getElementsByTagName("tr");

    for (var i = 1; i < rows.length; i++) {
        var cells = rows[i].getElementsByTagName("td");
        var id = cells[0].textContent.toLowerCase();
        var name = cells[1].textContent.toLowerCase();
        var position = cells[2].textContent.toLowerCase();

        var idMatch = id.includes(idFilter);
        var nameMatch = name.includes(nameFilter);
        var positionMatch = position.includes(positionFilter);

        // Lọc theo tháng và năm nếu bảng có cột Ngày (sau khi chọn tháng/năm)
        var dateMatch = true;
        if (cells.length > 3 && monthFilter && yearFilter) {
            var date = cells[3].textContent;
            var dateParts = date.split('/');
            var rowMonth = dateParts[1];
            var rowYear = dateParts[2];
            if (rowMonth !== monthFilter || rowYear !== yearFilter) {
                dateMatch = false;
            }
        }

        if (idMatch && nameMatch && positionMatch && dateMatch) {
            rows[i].style.display = "";
        } else {
            rows[i].style.display = "none";
        }
    }
}

// Gắn sự kiện lọc
['timekeeping-id-filter', 'timekeeping-name-filter', 'timekeeping-position-filter'].forEach(id => {
    document.getElementById(id).addEventListener('input', applyFilters);
});

// Gắn sự kiện chọn tháng năm
document.getElementById("timekeeping-month").addEventListener('change', () => {
    var month = document.getElementById("timekeeping-month").value;
    var year = document.getElementById("timekeeping-year").value;
    if (month && year) {
        renderTable(month, year);
    } else {
        renderDefaultTimekeepingTable();
    }
});
document.getElementById("timekeeping-year").addEventListener('change', () => {
    var month = document.getElementById("timekeeping-month").value;
    var year = document.getElementById("timekeeping-year").value;
    if (month && year) {
        renderTable(month, year);
    } else {
        renderDefaultTimekeepingTable();
    }
});

function exportToExcel() {
    try {
        var table = document.getElementById("timekeepingTable");
        var rows = table.getElementsByTagName("tr");
        var data = [];

        // Thu thập dữ liệu bảng
        for (var i = 0; i < rows.length; i++) {
            if (rows[i].style.display !== "none") {
                var row = [];
                for (var j = 0; j < rows[i].cells.length; j++) {
                    row.push(rows[i].cells[j].textContent);
                }
                data.push(row);
            }
        }

        if (data.length === 0) {
            console.warn("Không có dữ liệu để xuất Excel.");
            return;
        }

        // Sử dụng SheetJS để tạo file Excel
        var ws = XLSX.utils.aoa_to_sheet(data);
        var wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "TimekeepingData");
        XLSX.writeFile(wb, "timekeeping_data.xlsx");
    } catch (error) {
        console.error("Lỗi khi xuất Excel:", error);
    }
}

function exportEmployeesToExcel() {
    try {
        var table = document.getElementById("employeesTable");
        var rows = table.getElementsByTagName("tr");
        var data = [];

        // Thu thập dữ liệu bảng
        for (var i = 0; i < rows.length; i++) {
            if (rows[i].style.display !== "none") {
                var row = [];
                for (var j = 0; j < rows[i].cells.length; j++) {
                    row.push(rows[i].cells[j].textContent);
                }
                data.push(row);
            }
        }

        if (data.length === 0) {
            console.warn("Không có dữ liệu để xuất Excel.");
            return;
        }

        // Sử dụng SheetJS để tạo file Excel
        var ws = XLSX.utils.aoa_to_sheet(data);
        var wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "EmployeesData");
        XLSX.writeFile(wb, "employees_data.xlsx");
    } catch (error) {
        console.error("Lỗi khi xuất Excel cho tab Nhân viên:", error);
    }
}

// Hàm cập nhật bảng nhân viên
function updateEmployeesTable(employees) {
    var tbody = document.querySelector("#employeesTable tbody");
    if (!tbody) return;

    var html = '';
    employees.forEach(function(emp) {
        html += `<tr>
            <td>${emp.employee_id}</td>
            <td>${emp.name}</td>
            <td>${emp.position}</td>
        </tr>`;
    });
    tbody.innerHTML = html;
    filterEmployees();
}

// Hàm cập nhật bảng timekeeping
function updateTimekeepingTable(data) {
    window.timekeepingData = data.timekeeping; // Cập nhật biến toàn cục
    window.maxChecks = data.max_checks; // Cập nhật số cột Check n
    
    var month = document.getElementById("timekeeping-month").value;
    var year = document.getElementById("timekeeping-year").value;
    
    if (month && year) {
        renderTable(month, year);
    } else {
        renderDefaultTimekeepingTable();
    }
}

// Hàm lấy dữ liệu mới từ server
async function fetchData() {
    try {
        console.log('Bắt đầu fetch dữ liệu mới...');
        
        // Tạo URL với timestamp và cache buster
        const url = new URL('get_updated_data.php', window.location.href);
        url.searchParams.append('t', Date.now());
        url.searchParams.append('cb', Math.random()); // Cache buster
        
        // Thực hiện request với các header chống cache
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate, max-age=0',
                'Pragma': 'no-cache',
                'Expires': '-1',
                'X-Requested-With': 'XMLHttpRequest'
            },
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Parse JSON response
        const data = await response.json();
        console.log('Đã nhận dữ liệu từ server:', data);
        
        if (!data.employees || !data.timekeeping) {
            throw new Error('Dữ liệu không hợp lệ');
        }
        
        // Xóa và cập nhật lại toàn bộ DOM
        const employeesTable = document.querySelector("#employeesTable tbody");
        const timekeepingTable = document.querySelector("#timekeepingTable tbody");
        
        if (employeesTable) {
            console.log('Cập nhật bảng nhân viên...');
            while (employeesTable.firstChild) {
                employeesTable.removeChild(employeesTable.firstChild);
            }
            updateEmployeesTable(data.employees);
        }
        
        if (timekeepingTable) {
            console.log('Cập nhật bảng timekeeping...');
            while (timekeepingTable.firstChild) {
                timekeepingTable.removeChild(timekeepingTable.firstChild);
            }
            updateTimekeepingTable(data);
        }
        
        // Log chi tiết kết quả
        console.log('Hoàn thành cập nhật dữ liệu:', {
            timestamp: new Date().toLocaleTimeString(),
            employees: data.employees.length,
            timekeeping: data.timekeeping.length
        });
        
        return true; // Fetch thành công
        
    } catch (error) {
        console.error('Lỗi trong quá trình fetch dữ liệu:', error);
        throw error; // Ném lỗi để xử lý ở handler
    }
}

// Biến để lưu interval ID
let updateInterval;
let failedAttempts = 0;
const MAX_FAILED_ATTEMPTS = 3;

// Hàm khởi tạo cập nhật tự động
function initAutoUpdate() {
    console.log('Bắt đầu tự động cập nhật...');
    
    // Xóa interval cũ nếu có
    if (updateInterval) {
        clearInterval(updateInterval);
    }
    
    // Reset số lần thất bại
    failedAttempts = 0;
    
    // Cập nhật lần đầu
    fetchData().catch(error => {
        console.error('Lỗi khi cập nhật lần đầu:', error);
        handleFailedAttempt();
    });
    
    // Thiết lập interval mới (5 giây)
    updateInterval = setInterval(async function() {
        console.log('Đang cập nhật dữ liệu...', new Date().toLocaleTimeString());
        try {
            await fetchData();
            // Reset số lần thất bại nếu thành công
            failedAttempts = 0;
        } catch (error) {
            handleFailedAttempt();
        }
    }, 5000);
}

// Xử lý khi fetch thất bại
function handleFailedAttempt() {
    failedAttempts++;
    console.log(`Lần thử thất bại thứ ${failedAttempts}/${MAX_FAILED_ATTEMPTS}`);
    
    if (failedAttempts >= MAX_FAILED_ATTEMPTS) {
        console.log('Đã đạt số lần thử tối đa, đang tải lại trang...');
        window.location.reload();
    }
}

// Khởi tạo khi DOM đã load
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM đã load xong - bắt đầu khởi tạo...');
    
    // Khởi động cập nhật tự động
    initAutoUpdate();
    
    // Kiểm tra và mở tab đã lưu trước đó
    var activeTab = sessionStorage.getItem('activeTab') || 'Employees'; // Mặc định là 'Employees'
    var tablinks = document.getElementsByClassName('tablinks');
    for (var i = 0; i < tablinks.length; i++) {
        if (tablinks[i].getAttribute('onclick').includes(activeTab)) {
            tablinks[i].click();
            break;
        }
    }
    
    // Thêm event listener cho sự kiện visibilitychange
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            console.log('Tab được active - cập nhật dữ liệu mới');
            // Cập nhật ngay khi tab được active
            fetchData().catch(error => {
                console.error('Lỗi khi cập nhật sau khi active:', error);
                window.location.reload(); // Force reload nếu có lỗi
            });
        }
    });
    
    // Thêm event listener cho phím F5
    document.addEventListener('keydown', function(event) {
        if (event.key === 'F5') {
            event.preventDefault(); // Ngăn F5 mặc định
            console.log('Đã bấm F5 - cập nhật dữ liệu mới');
            fetchData().catch(error => {
                console.error('Lỗi khi cập nhật sau khi bấm F5:', error);
                window.location.reload(); // Force reload nếu có lỗi
            });
        }
    });
});