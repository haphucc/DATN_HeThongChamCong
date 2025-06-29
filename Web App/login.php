<?php
session_start();
require_once 'db_connect.php';

if (isset($_SESSION['user_id'])) {
    header("Location: index.php");
    exit();
}

// Xử lý đăng nhập
if ($_SERVER['REQUEST_METHOD'] == 'POST') {
    $username = trim($_POST['username']);
    $password = trim($_POST['password']);
    
    $stmt = $conn->prepare("SELECT * FROM account WHERE name = ?");
    $stmt->bind_param("s", $username);
    $stmt->execute();
    $result = $stmt->get_result();
    
    if ($result->num_rows == 1) {
        $user = $result->fetch_assoc();
        $hashed_password = hash('sha256', $password);
        if ($hashed_password === $user['password']) {
            $_SESSION['employee_id'] = $user['employee_id'];
            $_SESSION['name'] = $user['name'];
            $_SESSION['position'] = $user['position'];
            header("Location: index.php");
            exit();
        } else {
            $error = "Sai mật khẩu!";
        }
    } else {
        $error = "Tài khoản không tồn tại!";
    }
}
?>

<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="images/favicon.png" type="image/png">
    <title>A Facial Recognition - Đăng nhập</title>
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
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        .wrapper {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
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

        .content {
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 80%;
            max-width: 1200px;
            margin-top: 60px;
        }

        .login-container {
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            width: 400px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.18);
            text-align: center;
        }

        .input-box {
            position: relative;
            margin-bottom: 20px;
        }

        .input-field {
            font-size: 15px;
            background: #f1f1f1;
            color: #333;
            height: 50px;
            width: 100%;
            padding: 0 10px 0 45px;
            border: none;
            border-radius: 30px;
            outline: none;
            transition: .2s ease;
        }

        .input-field::placeholder {
            color: #888;
        }

        .input-field:focus {
            background: #e8e8e8;
            border-color: rgba(255, 255, 255, 0.5);
        }

        .input-box i {
            position: absolute;
            left: 20px;
            top: 50%;
            transform: translateY(-50%);
            color: #888;
            font-size: 20px;
        }

        .submit {
            width: 100%;
            padding: 15px;
            font-size: 16px;
            font-weight: 600;
            color: #fff;
            background: #ff5e62;
            border: none;
            border-radius: 30px;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-top: 10px;
        }

        .submit:hover {
            background: #e04e52;
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }

        .error-message {
            color: #ff6b6b;
            margin-bottom: 20px;
            font-size: 14px;
            background: rgba(255, 0, 0, 0.1);
            padding: 10px;
            border-radius: 5px;
        }

        .illustration {
            width: 600px;
            height: 450px;
        }

        .illustration img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        @media (max-width: 768px) {
            .content {
                flex-direction: column;
                gap: 30px;
                width: 100%;
                padding: 20px;
            }

            .login-container {
                width: 100%;
                max-width: 350px;
                padding: 30px;
                margin: 0 auto;
            }

            .input-field {
                font-size: 16px;
                height: 55px;
                padding: 0 15px 0 50px;
            }

            .input-box i {
                font-size: 22px;
                left: 15px;
            }

            .submit {
                font-size: 18px;
                padding: 18px;
            }

            .error-message {
                font-size: 16px;
                padding: 12px;
            }

            .illustration {
                display: none;
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
        }

        @media (max-width: 480px) {
            .login-container {
                padding: 20px;
                max-width: 300px;
            }

            .input-field {
                font-size: 14px;
                height: 50px;
                padding: 0 10px 0 45px;
            }

            .submit {
                font-size: 16px;
                padding: 15px;
            }

            .nav-logo p {
                font-size: 14px;
            }

            .nav-menu a {
                font-size: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="wrapper">
        <nav class="nav">
            <div class="nav-logo">
                <p>Facial Attendance System</p>
            </div>
            <div class="nav-menu">
                <a href="login.php">Đăng Nhập</a>
                <a href="#">......</a>
                <a href="#">......</a>
                <a href="#">......</a>
                <a href="about.php">Về Chúng Tôi</a>
            </div>
        </nav>

        <div class="content">
            <div class="login-container">
                <div class="top">
                    <!-- <header>Đăng nhập</header> -->
                </div>
                <?php if (isset($error)): ?>
                    <div class="error-message"><?php echo $error; ?></div>
                <?php endif; ?>
                <form method="POST" action="login.php">
                    <div class="input-box">
                        <i class="bx bx-user"></i>
                        <input type="text" class="input-field" name="username" placeholder="Tên đăng nhập" required>
                    </div>
                    <div class="input-box">
                        <i class="bx bx-lock-alt"></i>
                        <input type="password" class="input-field" name="password" placeholder="Mật khẩu" required>
                    </div>
                    <div class="input-box">
                        <input type="submit" class="submit" value="Đăng nhập">
                    </div>
                </form>
            </div>
            <div class="illustration">
                <img src="images/2.jpg" alt="Illustration">
            </div>
        </div>
    </div>
</body>
</html>