package com.qgrid.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.qgrid.mobile.ui.GameViewModel
import com.qgrid.mobile.ui.Line56App
import com.qgrid.mobile.ui.theme.Line56Theme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        setContent {
            val viewModel: GameViewModel = viewModel()
            val state = viewModel.state.collectAsStateWithLifecycle().value
            Line56Theme(highContrast = state.progress.settings.highContrast) {
                Line56App(
                    state = state,
                    viewModel = viewModel,
                )
            }
        }
    }
}
