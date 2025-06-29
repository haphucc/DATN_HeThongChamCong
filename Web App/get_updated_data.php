<?php
session_start();
require_once 'db_connect.php';

// Tắt cache
header("Cache-Control: no-store, no-cache, must-revalidate, max-age=0");
header("Cache-Control: post-check=0, pre-check=0", false);
header("Pragma: no-cache");

// Kiểm tra đăng nhập
if (!isset($_SESSION['employee_id'])) {
    http_response_code(401);
    die("Unauthorized");
}

// Lấy dữ liệu nhân viên
$employees_sql = "SELECT * FROM employees ORDER BY employee_id";
$employees_result = $conn->query($employees_sql);
$employees_data = [];

if ($employees_result->num_rows > 0) {
    while($row = $employees_result->fetch_assoc()) {
        $employees_data[] = $row;
    }
}

// Lấy dữ liệu timekeeping
$timekeeping_sql = "SELECT t.id, t.employee_id, t.date, t.time, t.name, t.position 
                    FROM timekeeping t 
                    ORDER BY t.date, t.time";
$timekeeping_result = $conn->query($timekeeping_sql);
$timekeeping_data = [];
$max_checks = 0;

if ($timekeeping_result->num_rows > 0) {
    $temp_data = [];
    while($row = $timekeeping_result->fetch_assoc()) {
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

// Trả về dữ liệu dưới dạng JSON
header('Content-Type: application/json');
echo json_encode([
    'employees' => $employees_data,
    'timekeeping' => array_values($timekeeping_data),
    'max_checks' => $max_checks
]);

$conn->close();
?>