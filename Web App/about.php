<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="images/favicon.png" type="image/png">
    <title>Facial Attendance System - Về chúng tôi</title>
    <link href='https://unpkg.com/boxicons@2.1.4/css/boxicons.min.css' rel='stylesheet'>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro&display=swap&subset=vietnamese:wght@400;500;600;700&display=swap');

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Be Vietnam Pro', sans-serif;
        }

        body {
            background: #f5f7fa;
            min-height: 81vh;
            display: flex;
            flex-direction: column;
            color: #333;
        }

        .wrapper {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 81vh;
            width: 100%;
            background: rgba(39, 39, 39, 0.1);
        }

        .nav {
            position: fixed;
            top: 0;
            width: 100%;
            height: 60px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #fff;
            padding: 0 50px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 100;
        }

        .nav-left {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .nav-logo p {
            color: #ff5e62;
            font-size: 20px;
            font-weight: 600;
        }

        .nav-menu {
            display: flex;
            gap: 20px;
        }

        .nav-menu a {
            color: #333;
            text-decoration: none;
            font-weight: 500;
            font-size: 16px;
            transition: color 0.3s;
        }

        .nav-menu a:hover {
            color: #ff5e62;
        }

        .hamburger {
            display: none;
            font-size: 24px;
            cursor: pointer;
            color: #333;
        }

        .sidebar {
            position: fixed;
            top: 60px;
            left: 0;
            width: 200px;
            padding: 20px;
            background: #fff;
            height: calc(100vh - 60px);
            border-right: 1px solid #ddd;
            z-index: 99;
            transition: transform 0.3s ease;
        }

        .sidebar ul {
            list-style: none;
        }

        .sidebar ul li {
            margin-bottom: 10px;
        }

        .sidebar ul li a {
            color: #666;
            text-decoration: none;
            font-size: 14px;
        }

        .sidebar ul li a:hover {
            color: #ff5e62;
        }

        .sidebar ul li a.active {
            color: #ff5e62;
            font-weight: bold;
        }

        .content {
            margin-left: 220px;
            margin-top: 80px;
            padding: 20px;
            width: 100%;
            max-width: 800px;
        }

        .content h1 {
            font-size: 28px;
            margin-bottom: 20px;
            color: #333;
        }

        .content p {
            font-size: 16px;
            line-height: 1.6;
            margin-bottom: 20px;
        }

        .content a {
            color: #ff5e62;
            text-decoration: none;
        }

        .content a:hover {
            text-decoration: underline;
        }

        .footer {
            background: #f5f7fa;
            padding: 20px;
            text-align: center;
            border-top: 1px solid #ddd;
            margin-top: 50px;
        }

        .footer a {
            color: #666;
            text-decoration: none;
            margin: 0 10px;
            font-size: 14px;
        }

        .footer a:hover {
            color: #ff5e62;
        }

        .footer p {
            font-size: 14px;
            color: #666;
            margin-top: 10px;
        }

        @media (max-width: 768px) {
            .hamburger {
                display: block;
            }

            .sidebar {
                transform: translateX(-100%);
            }

            .sidebar.active {
                transform: translateX(0);
            }

            .content {
                margin-left: 0;
                margin-top: 60px;
                padding: 20px;
                width: 100%;
                max-width: 100%;
            }

            .content h1 {
                font-size: 24px;
            }

            .content p {
                font-size: 16px;
                line-height: 1.8;
            }

            .nav {
                padding: 0 15px;
                height: 50px;
            }

            .nav-logo p {
                font-size: 16px;
            }

            .nav-menu {
                gap: 8px;
            }

            .nav-menu a {
                font-size: 12px;
            }

            .footer {
                padding: 15px;
            }

            .footer a {
                font-size: 12px;
                margin: 0 5px;
            }

            .footer p {
                font-size: 12px;
            }
        }

        @media (max-width: 480px) {
            .content h1 {
                font-size: 20px;
            }

            .content p {
                font-size: 14px;
                line-height: 1.6;
            }

            .nav-logo p {
                font-size: 14px;
            }

            .nav-menu a {
                font-size: 10px;
            }

            .hamburger {
                font-size: 20px;
            }
        }
    </style>
</head>
<body>
    <div class="wrapper">
        <nav class="nav">
            <div class="nav-left">
                <div class="hamburger" onclick="toggleSidebar()"><i class='bx bx-menu'></i></div>
                <div class="nav-logo">
                    <p>Facial Attendance System</p>
                </div>
            </div>
            <div class="nav-menu">
                <a href="login.php">Đăng Nhập</a>
                <a href="#">......</a>
                <a href="#">......</a>
                <a href="#">......</a>
                <a href="about.php">Về Chúng Tôi</a>
            </div>
        </nav>

        <div class="sidebar" id="sidebar">
            <ul>
                <li><a href="about.php" class="active">Giới Thiệu</a></li>
                <li><a href="contact.php">Liên Hệ</a></li>
            </ul>
        </div>

        <div class="content">
            <p>
                Hệ thống Attendance System được phát triển để quản lý và theo dõi thời gian làm việc của nhân viên một cách hiệu quả. Chúng tôi cung cấp giải pháp chấm công tự động, giúp doanh nghiệp tiết kiệm thời gian và nâng cao hiệu suất quản lý nhân sự.
            </p>
            <p>
                Được thành lập vào năm 2025, sứ mệnh của chúng tôi là mang đến công nghệ tiên tiến, dễ sử dụng và đáng tin cậy cho các tổ chức trên toàn cầu.
            </p>
            <p>
                Nếu bạn có câu hỏi về vấn đề bảo mật hoặc dữ liệu, vui lòng xem trang <a href="#">Chính sách bảo mật và điều khoản</a>.
            </p>
        </div>
    </div>

    <div class="footer">
        <a href="#">Privacy Policy</a>
        <a href="#">Terms of Service</a>
        <p>@Copyright 2025 Attendance System</p>
    </div>

    <script>
        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('active');
        }
    </script>
</body>
</html>