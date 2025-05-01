// src/theme.js
import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'dark', // enables dark mode
    primary: {
      main: '#7E57C2', // example primary color
    },
    secondary: {
      main: '#26a69a', // example secondary color
    },
    background: {
      default: '#121212',
      paper: '#1e1e1e',
    },
    text: {
      primary: '#ffffff',
      secondary: '#aaaaaa',
    },
  },
  typography: {
    fontFamily: 'Helvetica',
    h1: { fontWeight: 700 },
    h2: { fontWeight: 700 },
    // You can further customize other typography variants
  },
});

export default theme;
