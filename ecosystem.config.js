module.exports = {
  apps: [{
    name: 'verifit-backend',
    script: 'run.py',
    interpreter: 'python',
    cwd: '/mnt/hdd_sda/projects/VeriFit-Backend',
    env: {
      NODE_ENV: 'production',
      DATABASE_URL: 'postgresql://verifit_master:verifit123@verifit-db.cpk0oamsu0g6.us-west-1.rds.amazonaws.com:5432/verifit_db'
    },
    instances: 1,
    exec_mode: 'fork',
    watch: false,
    max_memory_restart: '1G',
    error_file: './logs/err.log',
    out_file: './logs/out.log',
    log_file: './logs/combined.log',
    time: true,
    restart_delay: 4000,
    max_restarts: 10,
    min_uptime: '10s',
    kill_timeout: 5000,
    listen_timeout: 3000,
    shutdown_with_message: true
  }]
};
