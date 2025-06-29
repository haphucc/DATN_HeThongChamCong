<?php
$host = 'localhost';
$port = 3306; // Cổng mặc định của MySQL
$user = 'root';
$password = '';
$database = 'database_datn';

// Tạo kết nối
$conn = new mysqli($host, $user, $password, $database, $port);

// Kiểm tra kết nối
if ($conn->connect_error) {
    die("Kết nối thất bại: " . $conn->connect_error);
}

// Lấy dữ liệu từ bảng employees
$employees_sql = "SELECT * FROM employees";
$employees_result = $conn->query($employees_sql);
if ($employees_result === FALSE) {
    die("Lỗi truy vấn employees: " . $conn->error);
}

// Lấy dữ liệu từ bảng timekeeping
$timekeeping_sql = "SELECT timekeeping.id, timekeeping.employee_id, timekeeping.date, timekeeping.time, timekeeping.name, timekeeping.position 
                    FROM timekeeping 
                    ORDER BY timekeeping.date, timekeeping.time";
$timekeeping_result = $conn->query($timekeeping_sql);
if ($timekeeping_result === FALSE) {
    die("Lỗi truy vấn timekeeping: " . $conn->error);
}

// Tạo mảng dữ liệu để hiển thị
$timekeeping_data = [];
$max_checks = 0; // Số lần chấm công tối đa trong một ngày
if ($timekeeping_result->num_rows > 0) {
    $temp_data = [];
    while ($row = $timekeeping_result->fetch_assoc()) {
        $employee_key = $row['employee_id'] . '_' . $row['date'];
        // Đổi định dạng ngày từ YYYY-MM-DD sang DD/MM/YYYY
        $date = date('d/m/Y', strtotime($row['date']));
        $time = date('H:i:s', strtotime($row['time']));
        
        if (!isset($temp_data[$employee_key])) {
            $temp_data[$employee_key] = [
                'employee_id' => $row['employee_id'],
                'name' => $row['name'],
                'position' => $row['position'],
                'date' => $date,
                'times' => []
            ];
        }
        $temp_data[$employee_key]['times'][] = $time;
    }

    // Tính số lần chấm công tối đa trong một ngày
    foreach ($temp_data as $data) {
        $check_count = count($data['times']);
        if ($check_count > $max_checks) {
            $max_checks = $check_count;
        }
        $timekeeping_data[] = $data;
    }
}
?>