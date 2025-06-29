<?php
session_start();
require_once 'db_connect.php';

// Kiểm tra đăng nhập
if (!isset($_SESSION['employee_id'])) {
    header("Location: login.php");
    exit();
}

// Kiểm tra quyền truy cập (chỉ manager và admin mới được xem)
if ($_SESSION['position'] = !'manager' && $_SESSION['position'] = !'admin') {
    echo "Bạn không có quyền truy cập trang này! <a href='logout.php'>Đăng xuất để thử lại</a>";
    exit();
}

// Bao gồm các file PHPMailer thủ công
require 'PHPMailer/src/Exception.php';
require 'PHPMailer/src/PHPMailer.php';
require 'PHPMailer/src/SMTP.php';

// Sử dụng namespace
use PHPMailer\PHPMailer\PHPMailer;
use PHPMailer\PHPMailer\Exception;

// Hàm gửi email OTP
function sendOTPEmail($email, $otp) {
    $mail = new PHPMailer(true);
    try {
        $mail->isSMTP();
        $mail->Host = 'smtp.gmail.com';
        $mail->SMTPAuth = true;
        $mail->Username = 'phuchatao2002@gmail.com';
        $mail->Password = 'pqij kzxo igqx hiks';
        $mail->SMTPSecure = 'tls';
        $mail->Port = 587;

        $mail->CharSet = 'UTF-8';
        $mail->Encoding = 'base64';

        $mail->setFrom('phuchatao2002@gmail.com', 'Facial Attendance System');
        $mail->addAddress($email);

        $mail->isHTML(true);
        $mail->Subject = 'Mã OTP để đặt lại mật khẩu';
        $mail->Body = "Mã OTP của bạn là: <b>$otp</b>. Mã này có hiệu lực trong 10 phút.";
        $mail->AltBody = "Mã OTP của bạn là: $otp. Mã này có hiệu lực trong 10 phút.";

        $mail->send();
        return true;
    } catch (Exception $e) {
        return false;
    }
}

// Xử lý đặt lại mật khẩu
if ($_SERVER['REQUEST_METHOD'] == 'POST' && isset($_POST['reset_password'])) {
    if (isset($_POST['step']) && $_POST['step'] == 1) {
        $old_password = trim($_POST['old_password']);
        $hashed_old_password = hash('sha256', $old_password);
        
        $stmt = $conn->prepare("SELECT * FROM account WHERE password = ? LIMIT 1");
        $stmt->bind_param("s", $hashed_old_password);
        $stmt->execute();
        $result = $stmt->get_result();
        
        if ($result->num_rows == 1) {
            $user = $result->fetch_assoc();
            $email = $user['email'];
            
            $otp = rand(100000, 999999);
            $_SESSION['reset_otp'] = $otp;
            $_SESSION['reset_email'] = $email;
            $_SESSION['otp_time'] = time();
            $_SESSION['reset_step'] = 2; // Lưu trạng thái bước 2
            
            if (sendOTPEmail($email, $otp)) {
                $message = "OTP đã được gửi đến email của bạn!";
                $show_reset_step = 2;
            } else {
                $error = "Không thể gửi OTP. Vui lòng thử lại!";
                $show_reset_step = 1;
                $_SESSION['reset_step'] = 1;
            }
        } else {
            $error = "Mật khẩu cũ không đúng!";
            $show_reset_step = 1;
            $_SESSION['reset_step'] = 1;
        }
    } elseif (isset($_POST['step']) && $_POST['step'] == 2) {
        $entered_otp = trim($_POST['otp']);
        $new_password = trim($_POST['new_password']);
        $confirm_password = trim($_POST['confirm_password']);
        
        if (time() - $_SESSION['otp_time'] > 600) {
            $error = "OTP đã hết hạn!";
            unset($_SESSION['reset_otp']);
            unset($_SESSION['reset_email']);
            unset($_SESSION['otp_time']);
            $show_reset_step = 1;
            $_SESSION['reset_step'] = 1;
        } elseif ($entered_otp != $_SESSION['reset_otp']) {
            $error = "OTP không đúng!";
            $show_reset_step = 2;
            $_SESSION['reset_step'] = 2;
        } elseif ($new_password !== $confirm_password) {
            $error = "Mật khẩu mới không khớp!";
            $show_reset_step = 2;
            $_SESSION['reset_step'] = 2;
        } else {
            $hashed_new_password = hash('sha256', $new_password);
            $stmt = $conn->prepare("UPDATE account SET password = ? WHERE email = ?");
            $stmt->bind_param("ss", $hashed_new_password, $_SESSION['reset_email']);
            
            if ($stmt->execute()) {
                $message = "Đổi mật khẩu thành công!";
                unset($_SESSION['reset_otp']);
                unset($_SESSION['reset_email']);
                unset($_SESSION['otp_time']);
                $show_reset_step = 1;
                $_SESSION['reset_step'] = 1;
            } else {
                $error = "Lỗi khi cập nhật mật khẩu!";
                $show_reset_step = 2;
                $_SESSION['reset_step'] = 2;
            }
        }
    }
}

// Tạo danh sách năm để chọn
$years = [];
$year_sql = "SELECT DISTINCT YEAR(date) as year 
             FROM timekeeping 
             ORDER BY year";
$year_result = $conn->query($year_sql);
if ($year_result && $year_result->num_rows > 0) {
    while ($row = $year_result->fetch_assoc()) {
        $years[] = $row['year'];
    }
}

// Danh sách tháng (từ 1 đến 12)
$months = [
    "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
    "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12"
];

// Chuyển $timekeeping_data và $max_checks sang JSON để sử dụng trong JavaScript
$timekeeping_data_json = json_encode($timekeeping_data);
$max_checks_json = json_encode($max_checks);
?>

<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="icon" href="images/favicon.png" type="image/png">
    <title>Facial Attendance System - Trang Quản Lý</title>
    <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro&display=swap&subset=vietnamese" rel="stylesheet">
    <link href='https://unpkg.com/boxicons@2.1.4/css/boxicons.min.css' rel='stylesheet'>
    <link rel="stylesheet" href="index.css">
    <style>
        .reset-password-container {
            max-width: 500px;
            margin: 20px auto;
            padding: 20px;
            background: #fff;
            border-radius: 10px;
            box-shadow: 0 0 8px rgba(0,0,0,0.1);
        }

        .reset-password-container h3 {
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 20px;
            font-weight: 600;
        }

        .form-group {
            margin-bottom: 15px;
            text-align: center;
        }

        .form-group label {
            display: block;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
            font-size: 14px;
        }

        .form-group input {
            width: 100%;
            padding: 10px 15px;
            font-size: 14px;
            border: 1px solid #ccc;
            border-radius: 8px;
            outline: none;
            transition: border-color 0.3s ease;
        }

        .form-group input:focus {
            border-color: #ff5e62;
        }

        .submit-btn {
            width: 150px; /* Giảm chiều dài của nút Nhận OTP */
            padding: 10px;
            font-size: 16px;
            font-weight: 600;
            color: #fff;
            background: #ff5e62;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            display: block; /* Đảm bảo nút là block để có thể căn giữa */
            margin: 0 auto; /* Căn giữa nút */
        }

        .submit-btn:hover {
            background: #e04e52;
        }

        .error-message, .success-message {
            margin-bottom: 20px;
            padding: 10px;
            border-radius: 5px;
            font-size: 14px;
            text-align: center;
            opacity: 1;
            transition: opacity 0.5s ease;
        }

        .error-message {
            color: #721c24;
            background: #f8d7da;
            border: 1px solid #f5c6cb;
        }

        .success-message {
            color: #155724;
            background: #d4edda;
            border: 1px solid #c3e6cb;
        }

        .fade-out {
            opacity: 0;
        }

        @media (max-width: 768px) {
            .reset-password-container {
                margin: 10px;
                padding: 15px;
            }

            .reset-password-container h3 {
                font-size: 18px;
            }

            .form-group input {
                font-size: 14px;
                padding: 8px 12px;
            }

            .submit-btn {
                font-size: 14px;
                padding: 8px;
            }
        }

        @media (max-width: 480px) {
            .reset-password-container {
                margin: 5px;
                padding: 10px;
            }

            .reset-password-container h3 {
                font-size: 16px;
            }

            .form-group input {
                font-size: 12px;
                padding: 6px 10px;
            }

            .submit-btn {
                font-size: 12px;
                padding: 6px;
            }
        }
    </style>
</head>
<body>
    <h1 class="page-title">Trang Quản Lý ADMIN</h1>
    <div class="container">
        <div class="main-content">
            <!-- Tab links -->
            <div class="tab">
                <button class="tablinks active" onclick="openTab(event, 'Employees')">Thông Tin Nhân viên</button>
                <button class="tablinks" onclick="openTab(event, 'Timekeeping')">Ghi Nhận Timekeeping</button>
                <button class="tablinks" onclick="openTab(event, 'ResetPassword')">Đặt Lại Mật Khẩu</button>
                <button class="tablinks" onclick="window.location.href='logout.php'" style="color: red;">Đăng Xuất</button>
            </div>

            <!-- Tab content for Employees -->
            <div id="Employees" class="tabcontent">
                <h2>Nhân viên</h2>
                <div class="filter-controls">
                    <input type="text" id="employee-id-filter" onkeyup="filterEmployees()" placeholder="Lọc theo Mã NV">
                    <input type="text" id="employee-name-filter" onkeyup="filterEmployees()" placeholder="Lọc theo Tên">
                    <input type="text" id="employee-position-filter" onkeyup="filterEmployees()" placeholder="Lọc theo Vị trí">
                    <button id="export-excel-employees" onclick="exportEmployeesToExcel()">Xuất Excel</button>
                </div>
                <div class="table-wrapper">
                    <table id="employeesTable">
                        <thead>
                            <tr>
                                <th>Mã NV</th>
                                <th>Tên</th>
                                <th>Vị trí</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php
                            if ($employees_result->num_rows > 0) {
                                while($row = $employees_result->fetch_assoc()) {
                                    echo "<tr>";
                                    echo "<td>" . $row["employee_id"] . "</td>";
                                    echo "<td>" . $row["name"] . "</td>";
                                    echo "<td>" . $row["position"] . "</td>";
                                    echo "</tr>";
                                }
                            } else {
                                echo "<tr><td colspan='3'>Không tìm thấy nhân viên</td></tr>";
                            }
                            ?>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Tab content for Timekeeping -->
            <div id="Timekeeping" class="tabcontent">
                <h2>Lịch sử chấm công nhân viên</h2>
                <?php if (empty($timekeeping_data)): ?>
                    <p>Chưa có dữ liệu chấm công. Vui lòng sử dụng chương trình chấm công để ghi nhận dữ liệu.</p>
                <?php else: ?>
                <div class="controls">
                    <label for="timekeeping-month">Tháng:</label>
                    <select id="timekeeping-month">
                        <option value="">Chọn tháng</option>
                        <?php
                        for ($i = 0; $i < 12; $i++) {
                            $month_value = sprintf("%02d", $i + 1);
                            echo "<option value='$month_value'>{$months[$i]}</option>";
                        }
                        ?>
                    </select>

                    <label for="timekeeping-year">Năm:</label>
                    <select id="timekeeping-year">
                        <option value="">Chọn năm</option>
                        <?php
                        foreach ($years as $year) {
                            echo "<option value='$year'>$year</option>";
                        }
                        ?>
                    </select>
                </div>
                <div class="filter-controls">
                    <input type="text" id="timekeeping-id-filter" placeholder="Lọc theo Mã NV">
                    <input type="text" id="timekeeping-name-filter" placeholder="Lọc theo Tên">
                    <input type="text" id="timekeeping-position-filter" placeholder="Lọc theo Vị trí">
                    <button id="export-excel" onclick="exportToExcel()">Xuất Excel</button>
                </div>
                <div class="table-wrapper">
                    <div class="table-container">
                        <table id="timekeepingTable">
                            <thead id="tableHead">
                                <tr>
                                    <th>Mã NV</th>
                                    <th>Tên</th>
                                    <th>Vị trí</th>
                                </tr>
                            </thead>
                            <tbody id="tableBody">
                                <?php
                                if (!empty($timekeeping_data)) {
                                    foreach ($timekeeping_data as $data) {
                                        echo "<tr>";
                                        echo "<td>" . $data['employee_id'] . "</td>";
                                        echo "<td>" . $data['name'] . "</td>";
                                        echo "<td>" . $data['position'] . "</td>";
                                        echo "</tr>";
                                    }
                                } else {
                                    echo "<tr><td colspan='3'>Không tìm thấy ghi nhận timekeeping</td></tr>";
                                }
                                ?>
                            </tbody>
                        </table>
                    </div>
                </div>
                <?php endif; ?>			
            </div>

            <!-- Tab content for Reset Password -->
            <div id="ResetPassword" class="tabcontent">
                <h2>Đặt lại mật khẩu</h2>
                <div class="reset-password-container">
                    <?php if (isset($error) && isset($show_reset_step)): ?>
                        <div class="error-message" id="notification"><?php echo $error; ?></div>
                    <?php endif; ?>
                    <?php if (isset($message) && isset($show_reset_step)): ?>
                        <div class="success-message" id="notification"><?php echo $message; ?></div>
                    <?php endif; ?>

                    <!-- Bước 1: Nhập mật khẩu cũ -->
                    <div id="reset-step1" style="<?php echo (isset($show_reset_step) && $show_reset_step == 2) ? 'display: none;' : ''; ?>">
                        <!-- <h3 style="text-align: center;">Nhập mật khẩu cũ để nhận OTP</h3> -->
                        <h3>Nhập mật khẩu cũ để nhận OTP</h3>

                        <form method="POST" action="index.php">
                            <input type="hidden" name="reset_password" value="1">
                            <input type="hidden" name="step" value="1">
                            <div class="form-group">
                                <label for="old_password"></label>
                                <input type="password" id="old_password" name="old_password" placeholder="Nhập mật khẩu cũ" required>
                            </div>
                            <button type="submit" class="submit-btn">Nhận OTP</button>
                        </form>
                    </div>

                    <!-- Bước 2: Nhập OTP và mật khẩu mới -->
                    <div id="reset-step2" style="<?php echo (!isset($show_reset_step) || $show_reset_step != 2) ? 'display: none;' : ''; ?>">
                        <h3>Nhập OTP và mật khẩu mới</h3>
                        <form method="POST" action="index.php">
                            <input type="hidden" name="reset_password" value="1">
                            <input type="hidden" name="step" value="2">
                            <div class="form-group">
                                <label for="otp">Mã OTP:</label>
                                <input type="text" id="otp" name="otp" placeholder="Nhập mã OTP" required>
                            </div>
                            <div class="form-group">
                                <label for="new_password">Mật khẩu mới:</label>
                                <input type="password" id="new_password" name="new_password" placeholder="Nhập mật khẩu mới" required>
                            </div>
                            <div class="form-group">
                                <label for="confirm_password">Xác nhận mật khẩu mới:</label>
                                <input type="password" id="confirm_password" name="confirm_password" placeholder="Xác nhận mật khẩu mới" required>
                            </div>
                            <button type="submit" class="submit-btn">Xác nhận</button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Thêm thư viện SheetJS từ CDN -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>
    <script>
        var timekeepingData = <?php echo $timekeeping_data_json; ?>;
        var maxChecks = <?php echo $max_checks_json; ?>;
    </script>
    <script src="scripts.js"></script>

    <script>
        // Tự động hiển thị bước 2 nếu OTP đã được gửi
        <?php if (isset($_SESSION['reset_step'])): ?>
            var resetStep = <?php echo json_encode($_SESSION['reset_step']); ?>;
            if (resetStep == 2) {
                document.getElementById('reset-step1').style.display = 'none';
                document.getElementById('reset-step2').style.display = 'block';
            }
        <?php endif; ?>

        // Xóa thông báo sau 3 giây
        document.addEventListener('DOMContentLoaded', function() {
            var notification = document.getElementById('notification');
            if (notification) {
                setTimeout(function() {
                    notification.classList.add('fade-out');
                    setTimeout(function() {
                        notification.remove();
                    }, 500); // Thời gian chờ cho hiệu ứng fade-out hoàn tất
                }, 3000); // Hiển thị thông báo trong 3 giây
            }
        });
    </script>

    <?php
    $conn->close();
    ?>
</body>
</html>