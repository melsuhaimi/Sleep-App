package com.melsuhaimi.sleepapp.bootstrap.core.di

import android.content.Context
import androidx.room.Room
import com.melsuhaimi.sleepapp.bootstrap.data.persistence.SleepDatabase
import com.melsuhaimi.sleepapp.bootstrap.data.persistence.SleepDatabaseMigrations
import com.melsuhaimi.sleepapp.bootstrap.data.settings.DataStoreSettingsRepository
import com.melsuhaimi.sleepapp.bootstrap.data.settings.SettingsRepository
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object PersistenceModule {
    @Provides
    @Singleton
    fun provideSleepDatabase(
        @ApplicationContext context: Context,
    ): SleepDatabase = Room.databaseBuilder(
        context,
        SleepDatabase::class.java,
        SleepDatabase.DATABASE_NAME,
    )
        .addMigrations(*SleepDatabaseMigrations.ALL)
        .build()
}

@Module
@InstallIn(SingletonComponent::class)
abstract class SettingsRepositoryModule {
    @Binds
    @Singleton
    abstract fun bindSettingsRepository(
        repository: DataStoreSettingsRepository,
    ): SettingsRepository
}
