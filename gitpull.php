?php

// Use in the “Post-Receive URLs” section of your GitHub repo.

if ( $_POST['https://github.com/AayushB2/test/blob/master/gitpull.php'] ) {
shell_exec( ‘C:\FTC\21-22\FtcRobotController-master && git reset –hard HEAD && git pull’ );
}

?>hi
