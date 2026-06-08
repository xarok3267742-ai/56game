package com.qgrid.mobile.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.qgrid.mobile.game.LEVEL_COUNT
import com.qgrid.mobile.game.ProgressState
import com.qgrid.mobile.game.ProgressRules
import com.qgrid.mobile.game.SettingsState
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map
import java.io.IOException

private val Context.progressDataStore: DataStore<Preferences> by preferencesDataStore(
    name = "qgrid_state",
)

class ProgressRepository(
    context: Context,
) {
    private val dataStore = context.applicationContext.progressDataStore

    val progressFlow: Flow<ProgressState> = dataStore.data
        .catch { exception ->
            if (exception is IOException) {
                emit(emptyPreferences())
            } else {
                throw exception
            }
        }
        .map { preferences ->
            ProgressState(
                onboardingSeen = preferences[Keys.ONBOARDING_SEEN] ?: false,
                completedLevelIds = ProgressRules.parseCompletedLevelIds(preferences[Keys.COMPLETED_LEVELS]),
                lastLevelId = ProgressRules.sanitizedLastLevelId(preferences[Keys.LAST_LEVEL_ID] ?: 1),
                settings = SettingsState(
                    hapticsEnabled = preferences[Keys.HAPTICS_ENABLED] ?: true,
                    highContrast = preferences[Keys.HIGH_CONTRAST] ?: false,
                    reduceMotion = preferences[Keys.REDUCE_MOTION] ?: false,
                ),
            )
        }

    suspend fun setOnboardingSeen() {
        dataStore.edit { preferences ->
            preferences[Keys.ONBOARDING_SEEN] = true
        }
    }

    suspend fun clearLocalState() {
        dataStore.edit { preferences ->
            preferences.clear()
        }
    }

    suspend fun markLevelCompleted(levelId: Int) {
        dataStore.edit { preferences ->
            val completed = ProgressRules.parseCompletedLevelIds(preferences[Keys.COMPLETED_LEVELS])
            preferences[Keys.COMPLETED_LEVELS] = ProgressRules.serializedCompletedLevelIds(completed + levelId)
            if (levelId in 1..LEVEL_COUNT) {
                preferences[Keys.LAST_LEVEL_ID] = ProgressRules.sanitizedLastLevelId(levelId)
            }
        }
    }

    suspend fun setLastLevel(levelId: Int) {
        dataStore.edit { preferences ->
            preferences[Keys.LAST_LEVEL_ID] = ProgressRules.sanitizedLastLevelId(levelId)
        }
    }

    suspend fun setHapticsEnabled(enabled: Boolean) {
        dataStore.edit { preferences ->
            preferences[Keys.HAPTICS_ENABLED] = enabled
        }
    }

    suspend fun setHighContrast(enabled: Boolean) {
        dataStore.edit { preferences ->
            preferences[Keys.HIGH_CONTRAST] = enabled
        }
    }

    suspend fun setReduceMotion(enabled: Boolean) {
        dataStore.edit { preferences ->
            preferences[Keys.REDUCE_MOTION] = enabled
        }
    }

    private object Keys {
        val ONBOARDING_SEEN = booleanPreferencesKey("onboarding_seen")
        val COMPLETED_LEVELS = stringPreferencesKey("completed_levels")
        val LAST_LEVEL_ID = intPreferencesKey("last_level_id")
        val HAPTICS_ENABLED = booleanPreferencesKey("haptics_enabled")
        val HIGH_CONTRAST = booleanPreferencesKey("high_contrast")
        val REDUCE_MOTION = booleanPreferencesKey("reduce_motion")
    }
}
