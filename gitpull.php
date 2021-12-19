?php

// Use in the “Post-Receive URLs” section of your GitHub repo.

if ( $_POST['payload'] ) {
shell_exec( ‘C:\FTC\21-22\FtcRobotController-master && git reset –hard HEAD && git pull’ );
}

?>hi
